from rest_framework.response import Response
from django.db import transaction
from rest_framework import viewsets
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, NotFound
from core.registry import get_licenca_db_config
from .models import ItensOrcamento, Orcamentos
from Entidades.models import Entidades
from .serializers import OrcamentosSerializer
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from parametros_admin.decorators import parametros_orcamentos_completo
from Pedidos.models import PedidoVenda, Itenspedidovenda

import logging
logger = logging.getLogger(__name__)


class OrcamentoViewSet(ModuloRequeridoMixin,viewsets.ModelViewSet):
    modulo_necessario = 'Orcamentos'  
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['pedi_empr', 'pedi_fili']
    search_fields = ['pedi_nume', 'pedi_forn']
    serializer_class = OrcamentosSerializer
    lookup_field = 'pedi_nume'
    search_fields = ['pedi_nume', 'pedi_forn']
    filterset_fields = ['pedi_empr', 'pedi_fili']
    
    
    
    def get_queryset(self):
       banco = get_licenca_db_config(self.request)
       queryset = Orcamentos.objects.using(banco).all()
       if banco:       

        cliente_nome = self.request.query_params.get('cliente_nome')
        empresa_id = self.request.query_params.get('pedi_empr')
        numero_orcamento = self.request.query_params.get('pedi_nume')



        if cliente_nome:
            ent_qs = Entidades.objects.using(banco).filter(enti_nome__icontains=cliente_nome)
            if empresa_id:
                ent_qs = ent_qs.filter(enti_empr=empresa_id)
            
            clientes_ids = list(ent_qs.values_list('enti_clie', flat=True))
            
            if clientes_ids:
                queryset = queryset.filter(pedi_forn__in=clientes_ids)
            else:
                queryset = queryset.none()

        if numero_orcamento:
            try:
                numero = int(numero_orcamento)
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
    
    
    @parametros_orcamentos_completo
    def create(self, request, *args, **kwargs):
        try:
            logger.info(f"[OrcamentoViewSet.create] request.data: {request.data}")
        except Exception as e:
            logger.error(f"Erro ao acessar request.data: {e}")

        serializer = self.get_serializer(data=request.data, context=self.get_serializer_context())
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except ValidationError as e:
            logger.warning(f"[OrcamentoViewSet.create] Erro de validação: {e.detail}")
            return Response({'errors': e.detail}, status=status.HTTP_400_BAD_REQUEST)



    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    
    
    @parametros_orcamentos_completo
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        pedido = serializer.save()
        return Response(self.get_serializer(pedido).data, status=status.HTTP_200_OK)
    
    
    
    def destroy(self, request, *args, **kwargs):
        orcamento = self.get_object()
        banco = get_licenca_db_config(self.request)
        
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")

       
        if ItensOrcamento.objects.using(banco).filter(
            iped_empr=orcamento.pedi_empr,
            iped_fili=orcamento.pedi_fili,
            iped_pedi=orcamento.pedi_nume
        ).exists():
            return Response(
                {"detail": "Não é possível excluir a Pedidos , Há itens associados."},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic(using=banco):
            orcamento.delete()
            logger.info(f"🗑️ Exclusão Pedido de casamento ID {orcamento.pedi_nume} concluída")

        return Response(status=status.HTTP_204_NO_CONTENT)
    

    @action(detail=True, methods=['post'], url_path='transformar-em-pedido')
    def transformar_em_pedido(self, request, *args, **kwargs):
        orcamento = self.get_object()
        banco = get_licenca_db_config(self.request)
        
        if not banco:
            logger.error("Banco de dados não encontrado.")
            return Response(
                {'error': 'Banco de dados não encontrado'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic(using=banco):
                # Importar os modelos necessários
                from Pedidos.models import PedidoVenda, Itenspedidovenda
                
                # Buscar o último número de pedido para gerar sequencial
                ultimo_pedido = PedidoVenda.objects.using(banco).filter(
                    pedi_empr=orcamento.pedi_empr,
                    pedi_fili=orcamento.pedi_fili
                ).order_by('-pedi_nume').first()
                
                novo_numero = (ultimo_pedido.pedi_nume + 1) if ultimo_pedido else 1
                
                # Criar o pedido espelhando os dados do orçamento
                pedido = PedidoVenda.objects.using(banco).create(
                    pedi_empr=orcamento.pedi_empr,
                    pedi_fili=orcamento.pedi_fili,
                    pedi_nume=novo_numero,
                    pedi_forn=orcamento.pedi_forn,
                    pedi_data=orcamento.pedi_data,
                    pedi_tota=orcamento.pedi_tota,
                    pedi_vend=orcamento.pedi_vend or '0',
                    pedi_obse=orcamento.pedi_obse or '',
                    pedi_canc=False,
                    pedi_fina='0',  # À vista por padrão
                    pedi_stat=0     # Pendente por padrão
                )
                
                # Buscar todos os itens do orçamento
                itens_orcamento = ItensOrcamento.objects.using(banco).filter(
                    iped_empr=orcamento.pedi_empr,
                    iped_fili=orcamento.pedi_fili,
                    iped_pedi=str(orcamento.pedi_nume)
                )
                
                # Criar os itens do pedido espelhando os itens do orçamento
                for item in itens_orcamento:
                    Itenspedidovenda.objects.using(banco).create(
                        iped_empr=pedido.pedi_empr,
                        iped_fili=pedido.pedi_fili,
                        iped_pedi=str(pedido.pedi_nume),
                        iped_item=item.iped_item,
                        iped_prod=item.iped_prod,
                        iped_quan=item.iped_quan,
                        iped_unit=item.iped_unit,
                        iped_tota=item.iped_tota,
                        iped_desc=item.iped_desc,
                        iped_unli=item.iped_unli,
                        iped_forn=item.iped_forn,
                        iped_data=item.iped_data,
                        iped_suto=0.00,  # Valor padrão
                        iped_fret=0.00,  # Valor padrão
                        iped_vend=int(orcamento.pedi_vend) if orcamento.pedi_vend and orcamento.pedi_vend.isdigit() else None,
                        iped_cust=0.00,  # Valor padrão
                        iped_tipo=1,     # Valor padrão
                        iped_desc_item=False,  # Valor padrão
                        iped_perc_desc=0.00,   # Valor padrão
                        iped_unme=None   # Valor padrão
                    )
                
                # VINCULAR O NÚMERO DO PEDIDO NO ORÇAMENTO
                orcamento.pedi_nume_pedi = pedido.pedi_nume
                orcamento.save(using=banco)
                
                logger.info(f"Orçamento {orcamento.pedi_nume} transformado em pedido {pedido.pedi_nume} e vinculado")
                
                return Response({
                    'message': 'Orçamento transformado em pedido com sucesso',
                    'pedido_numero': pedido.pedi_nume,
                    'orcamento_numero': orcamento.pedi_nume,
                    'vinculacao': f'Orçamento {orcamento.pedi_nume} agora está vinculado ao pedido {pedido.pedi_nume}'
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            logger.error(f"Erro ao transformar orçamento em pedido: {str(e)}")
            return Response({
                'error': 'Erro ao transformar orçamento em pedido',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'message': 'Orcamento transformado com sucesso'}, status=status.HTTP_200_OK)
            
        