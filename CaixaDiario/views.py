from rest_framework import viewsets, status, filters
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Max
from Pedidos.models import PedidoVenda, Itenspedidovenda
from django.db import transaction
from rest_framework.response import Response
from rest_framework.decorators import action
from core.registry import get_licenca_db_config
from core.middleware import get_licenca_slug
from rest_framework.permissions import IsAuthenticated
import logging
from datetime import datetime

from .models import Caixageral, Movicaixa
from .REST.serializers import CaixageralSerializer, MovicaixaSerializer  

logger = logging.getLogger(__name__)

class CaixageralViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CaixageralSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['caix_empr', 'caix_fili', 'caix_caix', 'caix_data', 'caix_oper', 'caix_aber']
    search_fields = ['caix_ecf', 'caix_obse_fech']
    ordering_fields = ['caix_data', 'caix_hora']
    ordering = ['caix_data']
    lookup_field = 'caix_empr' 

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        empresa_id = self.request.headers.get("X-Empresa")
        filial_id = self.request.headers.get("X-Filial")
        operador = self.request.query_params.get('oper')
        status = self.request.query_params.get('status')  

        if banco and empresa_id and filial_id:
            queryset = Caixageral.objects.using(banco).filter(
                caix_empr=empresa_id,
                caix_fili=filial_id
            )
            if operador:
                queryset = queryset.filter(caix_oper=operador)
            if status:
                queryset = queryset.filter(caix_aber=status)

            return queryset.order_by('-caix_data')
        
        return Caixageral.objects.none()

    def destroy(self, request, *args, **kwargs):
        banco = get_licenca_db_config(self.request)
        instance = self.get_object()

        # Exemplo básico: não deixar excluir se tiver algo associado (ajuste conforme regra)
        # Aqui só deixei para excluir direto, adapte se precisar de regra.
        with transaction.atomic(using=banco):
            instance.delete()
            logger.info(f"🗑️ Exclusão de Caixageral ID {instance.caix_empr} concluída")

        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context


class MovicaixaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MovicaixaSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['movi_empr', 'movi_fili', 'movi_caix', 'movi_data', 'movi_nume_vend', 'movi_tipo']
    search_fields = ['movi_nomi', 'movi_obse']
    ordering_fields = ['movi_data', 'movi_hora', 'movi_ctrl']
    ordering = ['-movi_data', '-movi_ctrl']
    lookup_field = 'movi_empr'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        empresa_id = self.request.headers.get("X-Empresa")
        filial_id = self.request.headers.get("X-Filial")

        if banco and empresa_id and filial_id:
            queryset = Movicaixa.objects.using(banco).filter(
                movi_empr=empresa_id,
                movi_fili=filial_id
            )
            return queryset
        return Movicaixa.objects.none()

    def destroy(self, request, *args, **kwargs):
        banco = get_licenca_db_config(self.request)
        instance = self.get_object()

        # Igual no Caixageral, exemplo simples
        with transaction.atomic(using=banco):
            instance.delete()
            logger.info(f"🗑️ Exclusão de Movicaixa ID {instance.movi_empr} concluída")

        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context



    @action(detail=False, methods=['post'])
    def iniciar_venda(self, request, slug=None):
        slug = get_licenca_slug()
        banco = get_licenca_db_config(self.request)
        empresa_id = self.request.headers.get("X-Empresa")
        filial_id = self.request.headers.get("X-Filial")
        
        # Pegar operador de forma mais robusta
        operador = (
            self.request.headers.get("usuario_id") or 
            self.request.headers.get("X-Usuario") or 
            self.request.data.get('operador')
        )

        cliente = request.data.get('cliente')
        vendedor = request.data.get('vendedor')
        caixa = request.data.get('caixa')

        if not all([cliente, vendedor, caixa]):
            return Response(
                {'detail': 'Cliente, vendedor e caixa são obrigatórios'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            caixa_aberto = Caixageral.objects.using(banco).filter(
                caix_empr=empresa_id,
                caix_fili=filial_id,
                caix_caix=caixa,
                caix_aber='A'
            ).first()

            if not caixa_aberto:
                return Response(
                    {'detail': 'Caixa não está aberto'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            with transaction.atomic(using=banco):

                ultimo_num_pedido = PedidoVenda.objects.using(banco).filter(
                    pedi_empr=empresa_id,
                    pedi_fili=filial_id
                ).aggregate(Max('pedi_nume'))['pedi_nume__max'] or 0

                ultimo_num_movimento = Movicaixa.objects.using(banco).filter(
                    movi_empr=empresa_id,
                    movi_fili=filial_id
                ).aggregate(Max('movi_nume_vend'))['movi_nume_vend__max'] or 0

                numero_venda = max(ultimo_num_pedido, ultimo_num_movimento) + 1
                
                ultimo_ctrl = Movicaixa.objects.using(banco).filter(
                    movi_empr=empresa_id,
                    movi_fili=filial_id,
                    movi_caix=caixa_aberto.caix_caix,
                    movi_data=datetime.today().date()
                ).aggregate(Max('movi_ctrl'))['movi_ctrl__max'] or 0


                ultimo_pedido = PedidoVenda.objects.using(banco).filter(
                    pedi_empr=empresa_id,
                    pedi_fili=filial_id,
                    pedi_nume=numero_venda,
                    pedi_forn=cliente,
                    pedi_vend=vendedor,
                    pedi_data=datetime.today().date(),
                    pedi_stat='0',
                ).first()

                if ultimo_pedido:
                   
                    ultimo_pedido.pedi_forn = cliente
                    ultimo_pedido.pedi_vend = vendedor
                    ultimo_pedido.pedi_data = datetime.today().date()
                    ultimo_pedido.pedi_hora = datetime.now().time()
                    ultimo_pedido.save(using=banco)
                else:
                    
                    PedidoVenda.objects.using(banco).create(
                        pedi_empr=empresa_id,
                        pedi_fili=filial_id,
                        pedi_nume=numero_venda,
                        pedi_forn=cliente,
                        pedi_vend=vendedor,
                        pedi_data=datetime.today().date(),
                        pedi_stat='0',  
                      )
                    '''Movicaixa.objects.using(banco).create(
                        movi_empr=empresa_id,
                        movi_fili=filial_id,
                        movi_caix=caixa_aberto.caix_caix,
                        movi_vend = vendedor,
                        movi_clie = cliente,
                        movi_nume_vend=numero_venda,
                        movi_hora=datetime.now().time(),
                        movi_data=datetime.today().date(),
                        movi_ctrl=ultimo_ctrl + 1,
                        movi_oper=vendedor,
                        movi_obse=f'Caixa  {caixa} Gerado por Mobile o Pedido de Venda {numero_venda}',
                    )'''

            return Response({
                'numero_venda': numero_venda,
                'cliente': cliente,
                'vendedor': vendedor,
                'caixa': caixa
            })

        except Exception as e:
            return Response(
                {'detail': f'Erro ao iniciar venda: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    @action(detail=False, methods=['post'])
    def adicionar_item(self, request, slug=None):
        banco = get_licenca_db_config(self.request)
        empresa_id = self.request.headers.get("X-Empresa")
        filial_id = self.request.headers.get("X-Filial")
        cliente = request.data.get('cliente')
        vendedor = request.data.get('vendedor')
        numero_venda = request.data.get('numero_venda')
        produto = request.data.get('produto')
        quantidade = request.data.get('quantidade')
        valor_unitario = request.data.get('valor_unitario')
        
        if not all([numero_venda, produto, quantidade, valor_unitario]):
            return Response(
                {'detail': 'Número da venda, produto, quantidade e valor unitário são obrigatórios'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic(using=banco):
              
                pedido = PedidoVenda.objects.using(banco).filter(
                    pedi_empr=empresa_id,
                    pedi_fili=filial_id,
                    pedi_nume=numero_venda
                ).first()
                
                if not pedido:
                    return Response(
                        {'detail': f'Pedido {numero_venda} não encontrado'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                
                valor_total = float(quantidade) * float(valor_unitario)
                
                item_existente = Itenspedidovenda.objects.using(banco).filter(
                    iped_empr=empresa_id,
                    iped_fili=filial_id,
                    iped_pedi=str(numero_venda),
                    iped_prod=produto
                ).first()
                
                if item_existente:
                    # Atualizar item existente
                    item_existente.iped_quan = float(item_existente.iped_quan) + float(quantidade)
                    item_existente.iped_tota = float(item_existente.iped_quan) * float(item_existente.iped_unit)
                    item_existente.save(using=banco)
                    item_obj = item_existente
                else:
                   
                    ultimo_item = Itenspedidovenda.objects.using(banco).filter(
                        iped_empr=empresa_id,
                        iped_fili=filial_id,
                        iped_pedi=str(numero_venda)
                    ).aggregate(Max('iped_item'))['iped_item__max'] or 0
                    
                    item_obj = Itenspedidovenda.objects.using(banco).create(
                        iped_empr=empresa_id,
                        iped_fili=filial_id,
                        iped_pedi=str(numero_venda),
                        iped_item=ultimo_item + 1,
                        iped_prod=produto,
                        iped_quan=quantidade,
                        iped_unit=valor_unitario,
                        iped_tota=valor_total,
                        iped_data=pedido.pedi_data,
                        iped_forn=pedido.pedi_forn
                    )
                
                # Recalcular total do pedido
                total_pedido = Itenspedidovenda.objects.using(banco).filter(
                    iped_empr=empresa_id,
                    iped_fili=filial_id,
                    iped_pedi=str(numero_venda)
                ).aggregate(Sum('iped_tota'))['iped_tota__sum'] or 0
                
                pedido.pedi_tota = total_pedido
                pedido.save(using=banco)
                
                movimento_existente = Movicaixa.objects.using(banco).filter(
                    movi_empr=empresa_id,
                    movi_fili=filial_id,
                    movi_nume_vend=numero_venda,
                    movi_tipo=1,
                    movi_obse__contains=f'Produto {produto}'
                ).first()
                
                if not movimento_existente:
                   
                    caixa_aberto = Caixageral.objects.using(banco).filter(
                        caix_empr=empresa_id,
                        caix_fili=filial_id,
                        caix_aber='A'
                    ).first()
                    
                    if caixa_aberto:
                        ultimo_ctrl = Movicaixa.objects.using(banco).filter(
                            movi_empr=empresa_id,
                            movi_fili=filial_id,
                            movi_data=caixa_aberto.caix_data
                        ).aggregate(Max('movi_ctrl'))['movi_ctrl__max'] or 0
                        
                        '''Movicaixa.objects.using(banco).create(
                            movi_empr=empresa_id,
                            movi_fili=filial_id,
                            movi_caix=caixa_aberto.caix_caix,
                            movi_nume_vend=numero_venda,
                            movi_vend = vendedor,
                            movi_clie = cliente,
                            movi_tipo=1,
                            movi_entr=valor_total,
                            movi_obse=f'Item - Produto {produto}',
                            movi_data=caixa_aberto.caix_data,
                            movi_hora=datetime.now().time(),
                            movi_ctrl=ultimo_ctrl + 1
                        )'''
                
                return Response({
                    'numero_venda': numero_venda,
                    'produto': produto,
                    'quantidade': float(quantidade),
                    'valor_unitario': float(valor_unitario),
                    'valor_total': float(valor_total),
                    'total_pedido': float(total_pedido),
                    'status': 'Item adicionado com sucesso'
                })
                
        except Exception as e:
            logger.error(f'Erro ao adicionar item: {str(e)}')
            return Response(
                {'detail': f'Erro ao adicionar item: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def adicionar_itens_lote(self, request, slug=None):
        banco = get_licenca_db_config(self.request)
        empresa_id = self.request.headers.get("X-Empresa")
        filial_id = self.request.headers.get("X-Filial")
        cliente = request.data.get('cliente')
        vendedor = request.data.get('vendedor')
        numero_venda = request.data.get('numero_venda')
        itens = request.data.get('itens', [])
        
        if not numero_venda or not itens:
            return Response(
                {'detail': 'Número da venda e itens são obrigatórios'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic(using=banco):
                # Verificar se o pedido existe
                pedido = PedidoVenda.objects.using(banco).filter(
                    pedi_empr=empresa_id,
                    pedi_fili=filial_id,
                    pedi_nume=numero_venda
                ).first()
                
                if not pedido:
                    return Response(
                        {'detail': f'Pedido {numero_venda} não encontrado'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                                
               
                total_pedido = 0
                for idx, item in enumerate(itens, 1):
                    valor_total = float(item['quantidade']) * float(item['valor_unitario'])
                    
                    Itenspedidovenda.objects.using(banco).create(
                        iped_empr=empresa_id,
                        iped_fili=filial_id,
                        iped_pedi=str(numero_venda),
                        iped_item=idx,
                        iped_prod=item['produto'],
                        iped_quan=item['quantidade'],
                        iped_unit=item['valor_unitario'],
                        iped_tota=valor_total,
                        iped_data=pedido.pedi_data,
                        iped_forn=pedido.pedi_forn
                    )
                    
                    total_pedido += valor_total
                
                # Atualizar total do pedido
                pedido.pedi_tota = total_pedido
                pedido.save(using=banco)
                
               
                caixa_aberto = Caixageral.objects.using(banco).filter(
                    caix_empr=empresa_id,
                    caix_fili=filial_id,
                    caix_aber='A'
                ).first()
                
                if caixa_aberto:
                    ultimo_ctrl = Movicaixa.objects.using(banco).filter(
                        movi_empr=empresa_id,
                        movi_fili=filial_id,
                        movi_data=caixa_aberto.caix_data
                    ).aggregate(Max('movi_ctrl'))['movi_ctrl__max'] or 0
                    
                    '''Movicaixa.objects.using(banco).create(
                        movi_empr=empresa_id,
                        movi_fili=filial_id,
                        movi_caix=caixa_aberto.caix_caix,
                        movi_nume_vend=numero_venda,
                        movi_vend = vendedor,
                        movi_clie = cliente,
                        movi_tipo=1,
                        movi_entr=total_pedido,
                        movi_said=total_pedido,
                        movi_obse=f'Venda {numero_venda} - {len(itens)} itens',
                        movi_data=caixa_aberto.caix_data,
                        movi_hora=datetime.now().time(),
                        movi_ctrl=ultimo_ctrl + 1
                    )'''
                
                return Response({
                    'numero_venda': numero_venda,
                    'total_itens': len(itens),
                    'total_pedido': float(total_pedido),
                    'status': 'Itens adicionados com sucesso'
                })
                
        except Exception as e:
            logger.error(f'Erro ao adicionar itens em lote: {str(e)}')
            return Response(
                {'detail': f'Erro ao adicionar itens: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def processar_pagamento(self, request, slug=None):
        slug = get_licenca_slug()
        banco = get_licenca_db_config(self.request)
        empresa_id = self.request.headers.get("X-Empresa")
        filial_id = self.request.headers.get("X-Filial")
        operador = (
            self.request.data.get('operador') or  # Primeiro: dados enviados explicitamente
            self.request.data.get('movi_oper') or  # Segundo: campo específico do movimento
            self.request.headers.get("usuario_id") or  # Terceiro: header usuario_id
            self.request.headers.get("X-Usuario") or  # Quarto: header X-Usuario
            (self.request.user.usua_codi if hasattr(self.request.user, 'usua_codi') else None) or  # Quinto: usuário autenticado
            (self.request.user.id if hasattr(self.request.user, 'id') else None)  # Sexto: fallback para id padrão
        )
        
        # Validar se o operador foi obtido
        if not operador:
            return Response(
                {'detail': 'Operador não identificado. Verifique se o usuário está autenticado ou envie o operador nos dados.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cliente = request.data.get('cliente')
        vendedor = request.data.get('vendedor')
        numero_venda = request.data.get('numero_venda')
        forma_pagamento = request.data.get('forma_pagamento')  # Códigos 51,52,54,60
        movi_tipo = request.data.get('movi_tipo')  # Códigos 1-6 (obrigatório)
        valor = request.data.get('valor')
        valor_pago = request.data.get('valor_pago')
        troco = request.data.get('troco')
        parcelas = request.data.get('parcelas', 1)
        
        
        MAPEAMENTO_FORMAS = {
            '51': '3',  # CARTÃO DE CRÉDITO
            '52': '4',  # CARTÃO DE DÉBITO  
            '54': '1',  # DINHEIRO
            '60': '6',  # PIX
        }
        
        TIPO_MOVIMENTO = [
            ('1', 'DINHEIRO'),
            ('2', 'CHEQUE'),
            ('3', 'CARTÃO DE CREDITO'),
            ('4', 'CARTÃO DE DEBITO'),
            ('5', 'CREDIÁRIO'),
            ('6', 'PIX'),
        ]
      
        tipo_movimento = None
        if movi_tipo:
            tipo_movimento = str(movi_tipo)
        elif forma_pagamento:
            tipo_movimento = MAPEAMENTO_FORMAS.get(str(forma_pagamento))
        
        if not all([numero_venda, valor]):
            return Response(
                {'detail': 'Número da venda e valor são obrigatórios'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not tipo_movimento:
            return Response(
                {'detail': 'Forma de pagamento inválida'},
                status=status.HTTP_400_BAD_REQUEST
            )
        

        tipos_validos = [choice[0] for choice in TIPO_MOVIMENTO]
        if tipo_movimento not in tipos_validos:
            return Response(
                {'detail': f'Tipo de movimento inválido. Opções válidas: {tipos_validos}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Buscar o caixa aberto
            caixa_aberto = Caixageral.objects.using(banco).filter(
                caix_empr=empresa_id,
                caix_fili=filial_id,
                caix_aber='A'
            ).first()

            if not caixa_aberto:
                return Response(
                    {'detail': 'Nenhum caixa aberto encontrado'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Buscar último controle
            ultimo_ctrl = Movicaixa.objects.using(banco).filter(
                movi_empr=empresa_id,
                movi_fili=filial_id,
                movi_data=caixa_aberto.caix_data
            ).aggregate(Max('movi_ctrl'))['movi_ctrl__max'] or 0

            # Criar movimento do pagamento
            movimento = Movicaixa.objects.using(banco).create(
                movi_empr=empresa_id,
                movi_fili=filial_id,
                movi_caix=caixa_aberto.caix_caix,
                movi_nume_vend=numero_venda,
                movi_tipo=tipo_movimento,  # Campo obrigatório (1-6)
                movi_tipo_movi=forma_pagamento,
                movi_vend=vendedor,
                movi_clie=cliente,
                movi_entr=valor_pago or valor,
                movi_said=troco if troco and float(troco) > 0 else 0,
                movi_obse=f'Venda {numero_venda}, Pagamento {dict(TIPO_MOVIMENTO).get(tipo_movimento)} - Parcelas: {parcelas}',
                movi_data=caixa_aberto.caix_data,
                movi_hora=datetime.now().time(),
                movi_ctrl=ultimo_ctrl + 1,
                movi_oper=operador, 
                movi_parc=str(parcelas) if parcelas else '1'
            )
            
            return Response({
                'success': True,
                'movimento_id': movimento.movi_ctrl,
                'movi_tipo': tipo_movimento,
                'movi_tipo_movi': forma_pagamento,
                'descricao_tipo': dict(TIPO_MOVIMENTO).get(tipo_movimento),
                'valor_pago': float(valor_pago or valor),
                'troco': movimento.movi_said,
                'parcelas': parcelas,
                'movi_entr': movimento.movi_entr,
                'movi_said': movimento.movi_said,
                'movi_oper': movimento.movi_oper,  
                'operador_usado': operador  
            })

        except Exception as e:
            logger.error(f'Erro ao processar pagamento: {str(e)}')
            return Response(
                {'detail': f'Erro ao processar pagamento: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def finalizar_venda(self, request, slug=None):
        slug = get_licenca_slug()
        banco = get_licenca_db_config(self.request)
        empresa_id = self.request.headers.get("X-Empresa")
        filial_id = self.request.headers.get("X-Filial")
        cliente = request.data.get('cliente')
        vendedor = request.data.get('vendedor')
        numero_venda = request.data.get('numero_venda')
        
        numero_venda = Movicaixa.objects.using(banco).filter(
            movi_empr=empresa_id,
            movi_fili=filial_id,
            movi_nume_vend=numero_venda
        ).first().movi_nume_vend

        try:
          
            movimentos = Movicaixa.objects.using(banco).filter(
                movi_empr=empresa_id,
                movi_fili=filial_id,
                movi_nume_vend=numero_venda
                
            )

   
            total_itens = movimentos.filter(movi_tipo=1).aggregate(
                total=Sum('movi_entr')
            )['total'] or 0

            total_pagamentos = movimentos.exclude(movi_tipo=1).aggregate(
                total=Sum('movi_entr') 
            )['total'] or 0

            pedido = PedidoVenda.objects.using(banco).filter(
                pedi_empr=empresa_id,
                pedi_fili=filial_id,
                pedi_nume=numero_venda
            ).first()

            if pedido:
                pedido.pedi_stat = '0' 
                pedido.save(using=banco)

            return Response({
                'numero_venda': numero_venda,
                'total_itens': float(total_itens),
                'total_pagamentos': float(total_pagamentos),
                'status': 'Finalizada'
            })

        except Exception as e:
            return Response(
                {'detail': f'Erro ao finalizar venda: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
