from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from .base import BaseMultiDBModelViewSet
from ..models import WorkflowSetor, OrdemServicoFaseSetor, OrdemServicoVoltagem
from ..serializers import WorkflowSetorSerializer, OrdemServicoFaseSetorSerializer, OrdemServicoVoltagemSerializer
from core.registry import get_licenca_db_config

class OrdemServicoFaseSetorViewSet(BaseMultiDBModelViewSet):
    """ViewSet para consultar fases de setores (somente leitura)"""
    modulo_necessario = 'OrdemdeServico'
    queryset = OrdemServicoFaseSetor.objects.all()
    serializer_class = OrdemServicoFaseSetorSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['osfs_codi', 'osfs_nome']
    ordering_fields = ['osfs_codi', 'osfs_nome']
    search_fields = ['osfs_nome']
    http_method_names = ['get']  # Apenas consulta (tabela não gerenciada)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

class OrdemServicoVoltagemViewSet(BaseMultiDBModelViewSet):
    """ViewSet para gerenciar voltagens de O.S."""
    modulo_necessario = 'OrdemdeServico'
    queryset = OrdemServicoVoltagem.objects.all()
    serializer_class = OrdemServicoVoltagemSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['osvo_codi', 'osvo_nome']
    ordering_fields = ['osvo_codi', 'osvo_nome']
    search_fields = ['osvo_nome']
    http_method_names = ['get']

class WorkflowSetorViewSet(BaseMultiDBModelViewSet):
    """ViewSet para gerenciar configurações de workflow entre setores"""
    modulo_necessario = 'OrdemdeServico'
    queryset = WorkflowSetor.objects.all()
    serializer_class = WorkflowSetorSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['wkfl_seto_orig', 'wkfl_seto_dest', 'wkfl_ativo']
    ordering_fields = ['wkfl_orde', 'wkfl_seto_orig', 'wkfl_seto_dest']
    search_fields = ['wkfl_seto_orig', 'wkfl_seto_dest']

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context
