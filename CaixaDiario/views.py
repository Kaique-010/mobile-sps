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
from .serializers import CaixageralSerializer, MovicaixaSerializer  

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

                ultimo_numero = Movicaixa.objects.using(banco).filter(
                    movi_empr=empresa_id,
                    movi_fili=filial_id
                ).aggregate(Max('movi_nume_vend'))['movi_nume_vend__max'] or 0

                numero_venda = ultimo_numero + 1

                ultimo_pedido = PedidoVenda.objects.using(banco).filter(
                    pedi_empr=empresa_id,
                    pedi_fili=filial_id,
                    pedi_nume=numero_venda,
                ).first()

                if ultimo_pedido:
                   
                    ultimo_pedido.pedi_clie = cliente
                    ultimo_pedido.pedi_vend = vendedor
                    ultimo_pedido.pedi_data = datetime.today().date()
                    ultimo_pedido.pedi_hora = datetime.now().time()
                    ultimo_pedido.save(using=banco)
                else:
                    
                    PedidoVenda.objects.using(banco).create(
                        pedi_empr=empresa_id,
                        pedi_fili=filial_id,
                        pedi_nume=numero_venda,
                        pedi_clie=cliente,
                        pedi_vend=vendedor,
                        pedi_data=datetime.today().date(),
                        pedi_hora=datetime.now().time(),
                        pedi_stat='P',  
                        pedi_caix=caixa_aberto.caix_caix
                      )
                    Movicaixa.objects.using(banco).create(
                        movi_empr=empresa_id,
                        movi_fili=filial_id,
                        movi_caix=caixa_aberto.caix_caix,
                        movi_vend = vendedor,
                        movi_clie = cliente,
                        movi_nume_vend=numero_venda,
                        movi_obse=f'Pedido de Venda {numero_venda}',
                        movi_hora=datetime.now().time(),
                        movi_data=datetime.today().date(),
                    )

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
                
                # Verificar se já existe movimento de caixa para este item específico
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
                        
                        Movicaixa.objects.using(banco).create(
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
                        )
                
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
                    
                    Movicaixa.objects.using(banco).create(
                        movi_empr=empresa_id,
                        movi_fili=filial_id,
                        movi_caix=caixa_aberto.caix_caix,
                        movi_nume_vend=numero_venda,
                        movi_vend = vendedor,
                        movi_clie = cliente,
                        movi_tipo=1,
                        movi_entr=total_pedido,
                        movi_obse=f'Venda {numero_venda} - {len(itens)} itens',
                        movi_data=caixa_aberto.caix_data,
                        movi_hora=datetime.now().time(),
                        movi_ctrl=ultimo_ctrl + 1
                    )
                
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
        cliente = request.data.get('cliente')
        vendedor = request.data.get('vendedor')
        numero_venda = request.data.get('numero_venda')
        forma_pagamento = request.data.get('forma_pagamento')
        valor = request.data.get('valor')
        troco = request.data.get('troco')
        
        if not all([numero_venda, forma_pagamento, valor]):
            return Response(
                {'detail': 'Dados do pagamento incompletos'},
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
                movi_tipo_movi=forma_pagamento,
                movi_vend = vendedor,
                movi_clie = cliente,
                movi_entr=valor,
                movi_obse=f'Pagamento - Forma: {forma_pagamento}',
                movi_data=caixa_aberto.caix_data,
                movi_hora=datetime.now().time(),
                movi_ctrl=ultimo_ctrl + 1,
                
            )

            return Response(MovicaixaSerializer(movimento).data)

        except Exception as e:
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
                total=Sum('movi_entr') and Sum('movi_said')
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
