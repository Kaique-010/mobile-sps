from rest_framework import viewsets, status, filters
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Max
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
        
        # Validar dados da venda
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

           
            ultimo_numero = Movicaixa.objects.using(banco).filter(
                movi_empr=empresa_id,
                movi_fili=filial_id
            ).aggregate(Max('movi_nume_vend'))['movi_nume_vend__max'] or 0

            numero_venda = ultimo_numero + 1

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
        slug = get_licenca_slug()
        banco = get_licenca_db_config(self.request)
        empresa_id = self.request.headers.get("X-Empresa")
        filial_id = self.request.headers.get("X-Filial")

        # Validar dados do item da venda
        numero_venda = request.data.get('numero_venda')
        produto = request.data.get('produto')
        quantidade = request.data.get('quantidade')
        valor_unitario = request.data.get('valor_unitario')
        
        if not all([numero_venda, produto, quantidade]):
            return Response(
                {'detail': 'Dados do item incompletos'},
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

            valor_total = float(quantidade) * float(valor_unitario)

            # Buscar último controle
            ultimo_ctrl = Movicaixa.objects.using(banco).filter(
                movi_empr=empresa_id,
                movi_fili=filial_id,
                movi_data=caixa_aberto.caix_data
            ).aggregate(Max('movi_ctrl'))['movi_ctrl__max'] or 0

            # Criar movimento do item
            movimento = Movicaixa.objects.using(banco).create(
                movi_empr=empresa_id,
                movi_fili=filial_id,
                movi_caix=caixa_aberto.caix_caix,
                movi_vend=numero_venda,
                movi_tipo=1,  # Tipo 1 = Item de venda
                movi_entr=valor_total,
                movi_obse=f'Produto: {produto}, Qtd: {quantidade}',
                movi_data=caixa_aberto.caix_data,
                movi_hora=datetime.now().time(),
                movi_ctrl=ultimo_ctrl + 1
            )

            return Response(MovicaixaSerializer(movimento).data)

        except Exception as e:
            return Response(
                {'detail': f'Erro ao adicionar item: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def processar_pagamento(self, request, slug=None):
        slug = get_licenca_slug()
        banco = get_licenca_db_config(self.request)
        empresa_id = self.request.headers.get("X-Empresa")
        filial_id = self.request.headers.get("X-Filial")

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
    def finalizar_venda(self, requestslug=None):
        slug = get_licenca_slug()
        banco = get_licenca_db_config(self.request)
        empresa_id = self.request.headers.get("X-Empresa")
        filial_id = self.request.headers.get("X-Filial")

        numero_venda = request.data.get('numero_venda')
        
        if not numero_venda:
            return Response(
                {'detail': 'Número da venda é obrigatório'},
                status=status.HTTP_400_BAD_REQUEST
            )

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

            if total_pagamentos < total_itens:
                return Response(
                    {'detail': 'Valor pago é menor que o total da venda'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                

            return Response({
                'numero_venda': numero_venda,
                'total_itens': total_itens,
                'total_pagamentos': total_pagamentos,
                'status': 'Finalizada'
            })

        except Exception as e:
            return Response(
                {'detail': f'Erro ao finalizar venda: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
