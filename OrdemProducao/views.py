from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from django.db import transaction
from .models import Ordemproducao, Ordemprodfotos, Ordemproditens, Ordemprodmate, Ordemprodetapa
from core.registry import get_licenca_db_config
from rest_framework.permissions import IsAuthenticated
from .serializers import (
    OrdemproducaoSerializer, 
    OrdemprodfotosSerializer, 
    OrdemproditensSerializer, 
    OrdemprodmateSerializer,
    OrdemprodetapaSerializer
)
from core.decorator import modulo_necessario, ModuloRequeridoMixin
import logging

logger = logging.getLogger(__name__)

class BaseMultiDBModelViewSet(ModuloRequeridoMixin, ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_banco(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error(f"Banco de dados não encontrado para {self.__class__.__name__}")
            raise NotFound("Banco de dados não encontrado.")
        return banco

    def get_queryset(self):
        return super().get_queryset().using(self.get_banco())

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = self.get_banco()
        return context

    @transaction.atomic(using='default')
    def create(self, request, *args, **kwargs):
        banco = self.get_banco()
        data = request.data
        is_many = isinstance(data, list)
        serializer = self.get_serializer(data=data, many=is_many)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic(using=banco):
            serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        banco = self.get_banco()
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic(using=banco):
            serializer.save()
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        banco = self.get_banco()
        instance = self.get_object()
        with transaction.atomic(using=banco):
            self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

class OrdemproducaoViewSet(BaseMultiDBModelViewSet):
    modulo = 'OrdemProducao'
    queryset = Ordemproducao.objects.all()
    serializer_class = OrdemproducaoSerializer
    filterset_fields = ['orpr_tipo', 'orpr_codi', 'orpr_entr', 'orpr_clie', 'orpr_stat']
    search_fields = ['orpr_tipo', 'orpr_codi', 'orpr_clie', 'orpr_nuca', 'cliente_nome']
    ordering_fields = ['orpr_tipo', 'orpr_codi', 'orpr_entr', 'orpr_clie', 'orpr_prev']
    ordering = ['-orpr_codi']
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Endpoint para dados do dashboard de ordens"""
        banco = self.get_banco()
        
        # Estatísticas gerais
        total_ordens = self.get_queryset().count()
        ordens_abertas = self.get_queryset().filter(orpr_stat=1).count()
        ordens_producao = self.get_queryset().filter(orpr_stat=2).count()
        ordens_finalizadas = self.get_queryset().filter(orpr_stat=3).count()
        
        # Ordens por tipo
        ordens_por_tipo = {}
        for tipo in ['1', '2', '3', '4']:
            ordens_por_tipo[tipo] = self.get_queryset().filter(orpr_tipo=tipo).count()
        
        # Ordens em atraso
        from django.utils import timezone
        ordens_atrasadas = self.get_queryset().filter(
            orpr_prev__lt=timezone.now(),
            orpr_stat__in=[1, 2]
        ).count()
        
        return Response({
            'total_ordens': total_ordens,
            'ordens_abertas': ordens_abertas,
            'ordens_producao': ordens_producao,
            'ordens_finalizadas': ordens_finalizadas,
            'ordens_por_tipo': ordens_por_tipo,
            'ordens_atrasadas': ordens_atrasadas,
        })
    
    @action(detail=True, methods=['post'])
    def iniciar_producao(self, request, pk=None):
        """Inicia a produção de uma ordem"""
        ordem = self.get_object()
        ordem.orpr_stat = 2  # Em produção
        ordem.save()
        
        return Response({'message': 'Produção iniciada com sucesso'})
    
    @action(detail=True, methods=['post'])
    def finalizar_ordem(self, request, pk=None):
        """Finaliza uma ordem de produção"""
        ordem = self.get_object()
        ordem.orpr_stat = 3  # Finalizada
        ordem.orpr_fech = timezone.now()
        ordem.save()
        
        return Response({'message': 'Ordem finalizada com sucesso'})

class OrdemprodfotosViewSet(BaseMultiDBModelViewSet):
    modulo = 'OrdemProducao'
    queryset = Ordemprodfotos.objects.all()
    serializer_class = OrdemprodfotosSerializer
    filterset_fields = ['orpr_codi', 'orpr_empr', 'orpr_fili']

class OrdemproditensViewSet(BaseMultiDBModelViewSet):
    modulo = 'OrdemProducao'
    queryset = Ordemproditens.objects.all()
    serializer_class = OrdemproditensSerializer
    filterset_fields = ['orpr_codi', 'orpr_fili', 'orpr_pedi']

class OrdemprodmateViewSet(BaseMultiDBModelViewSet):
    modulo = 'OrdemProducao'
    queryset = Ordemprodmate.objects.all()
    serializer_class = OrdemprodmateSerializer
    filterset_fields = ['orpm_orpr', 'orpm_prod']

class OrdemprodetapaViewSet(BaseMultiDBModelViewSet):
    modulo = 'OrdemProducao'
    queryset = Ordemprodetapa.objects.all()
    serializer_class = OrdemprodetapaSerializer
    filterset_fields = ['opet_orpr', 'opet_func', 'opet_etap']
    
    

    
