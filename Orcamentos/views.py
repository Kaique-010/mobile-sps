from rest_framework.response import Response
from django.db import transaction
from rest_framework import viewsets
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, NotFound
from core.registry import get_licenca_db_config
from .models import ItensOrcamento, Orcamentos
from Entidades.models import Entidades
from .serializers import OrcamentosSerializer
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend


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
    


