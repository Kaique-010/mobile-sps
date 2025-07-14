from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.decorators import action
from django.db import transaction
from core.registry import get_licenca_db_config
from .models import Itenspedidovenda, PedidoVenda
from Entidades.models import Entidades
from .serializers import PedidoVendaSerializer
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from parametros_admin.permissions import PermissaoAdministrador
from parametros_admin.integracao_pedidos import reverter_estoque_pedido, obter_status_estoque_pedido
from parametros_admin.decorators import parametros_pedidos_completo

import logging
logger = logging.getLogger(__name__)


class PedidoVendaViewSet(ModuloRequeridoMixin,viewsets.ModelViewSet):
    modeulo_necessario = 'Pedidos'  
    permission_classes = [IsAuthenticated]
    serializer_class = PedidoVendaSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    lookup_field = 'pedi_nume'
    search_fields = ['pedi_nume', 'pedi_forn']
    filterset_fields = ['pedi_empr', 'pedi_fili']
    
    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        queryset = PedidoVenda.objects.using(banco).all().order_by('pedi_nume')
        if banco:       
            cliente_nome = self.request.query_params.get('cliente_nome')
            numero_pedido = self.request.query_params.get('pedi_nume')
            empresa_id = self.request.query_params.get('pedi_empr')

            if cliente_nome:
                ent_qs = Entidades.objects.using(banco).filter(enti_nome__icontains=cliente_nome)
                if empresa_id:
                    ent_qs = ent_qs.filter(enti_empr=empresa_id)
                clientes_ids = list(ent_qs.values_list('enti_clie', flat=True))
                if clientes_ids:
                    queryset = queryset.filter(pedi_forn__in=clientes_ids)
                else:
                    queryset = queryset.none()

            if numero_pedido:
                try:
                    numero = int(numero_pedido)
                    queryset = queryset.filter(pedi_nume=numero)
                except ValueError:
                    queryset = queryset.none()

            return queryset 
        else:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")


    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context
    
    @parametros_pedidos_completo
    def create(self, request, *args, **kwargs):
        print(f"🎯 [VIEW] Recebendo requisição de criação de pedido")
        print(f"🎯 [VIEW] Dados da requisição: {request.data}")
        
        try:
            logger.info(f"[PedidoVendaViewSet.create] request.data: {request.data}")
        except Exception as e:
            logger.error(f"Erro ao acessar request.data: {e}")

        serializer = self.get_serializer(data=request.data, context=self.get_serializer_context())
        try:
            serializer.is_valid(raise_exception=True)
            print(f"🎯 [VIEW] Dados validados com sucesso, criando pedido...")
            self.perform_create(serializer)
            print(f"🎯 [VIEW] Pedido criado com sucesso")
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except ValidationError as e:
            print(f"❌ [VIEW] Erro de validação: {e.detail}")
            logger.warning(f"[PedidoVendaViewSet.create] Erro de validação: {e.detail}")
            return Response({'errors': e.detail}, status=status.HTTP_400_BAD_REQUEST)
    
    @parametros_pedidos_completo
    def update(self, request, *args, **kwargs):
        print(f"🎯 [VIEW] Recebendo requisição de atualização de pedido")
        print(f"🎯 [VIEW] Dados da requisição: {request.data}")
        
        instance = self.get_object()
        print(f"🎯 [VIEW] Atualizando pedido {instance.pedi_nume}")
        
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        print(f"🎯 [VIEW] Dados validados com sucesso, atualizando pedido...")
        pedido = serializer.save()
        print(f"🎯 [VIEW] Pedido atualizado com sucesso")
        return Response(self.get_serializer(pedido).data, status=status.HTTP_200_OK)
    
    
    def destroy(self, request, *args, **kwargs):
        pedido = self.get_object()
        banco = get_licenca_db_config(self.request)
        
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")

        # Reverter estoque antes de excluir
        try:
            resultado_estoque = reverter_estoque_pedido(pedido, request)
            if not resultado_estoque.get('sucesso', True):
                logger.warning(f"Erro ao reverter estoque: {resultado_estoque.get('erro')}")
            elif resultado_estoque.get('processado'):
                logger.info(f"Estoque revertido para pedido {pedido.pedi_nume}")
        except Exception as e:
            logger.error(f"Erro ao reverter estoque: {e}")

        with transaction.atomic(using=banco):
            # Excluir itens do pedido
            Itenspedidovenda.objects.using(banco).filter(
                iped_empr=pedido.pedi_empr,
                iped_fili=pedido.pedi_fili,
                iped_pedi=pedido.pedi_nume
            ).delete()
            
            # Excluir pedido
            pedido.delete()
            logger.info(f"🗑️ Exclusão Pedido ID {pedido.pedi_nume} concluída")

        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def cancelar_pedido(self, request, pedi_nume=None):
        """
        Cancela um pedido e reverte o estoque se configurado
        """
        try:
            pedido = self.get_object()
            banco = get_licenca_db_config(request)
            
            if not banco:
                return Response(
                    {'erro': 'Banco de dados não encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Verificar se pedido já está cancelado
            if pedido.pedi_stat == '4':  # Cancelado
                return Response(
                    {'erro': 'Pedido já está cancelado'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic(using=banco):
                # Reverter estoque
                resultado_estoque = reverter_estoque_pedido(pedido, request)
                
                # Atualizar status do pedido
                pedido.pedi_stat = '4'  # Cancelado
                pedido.pedi_canc = True
                pedido.save(using=banco)
                
                logger.info(f"Pedido {pedido.pedi_nume} cancelado")
                
                return Response({
                    'sucesso': True,
                    'mensagem': f'Pedido {pedido.pedi_nume} cancelado com sucesso',
                    'estoque_revertido': resultado_estoque
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"Erro ao cancelar pedido: {e}")
            return Response(
                {'erro': 'Erro interno ao cancelar pedido'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def status_estoque(self, request, pedi_nume=None):
        """
        Obtém status do estoque relacionado ao pedido
        """
        try:
            pedido = self.get_object()
            
            status_estoque = obter_status_estoque_pedido(
                pedido.pedi_nume,
                pedido.pedi_empr,
                pedido.pedi_fili,
                request
            )
            
            return Response(status_estoque, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erro ao obter status do estoque: {e}")
            return Response(
                {'erro': 'Erro ao obter status do estoque'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )