from rest_framework import pagination
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .base import BaseMultiDBModelViewSet
from ..models import HistoricoWorkflow
from ..serializers_historico import HistoricoWorkflowSerializer
from core.registry import get_licenca_db_config
from ..services import historico_service

class PaginacaoResultados(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class HistoricoWorkflowViewSet(BaseMultiDBModelViewSet):
    """
    Endpoint para histórico de workflows.
    Calcula o tempo que cada OS ficou em cada setor.
    """
    serializer_class = HistoricoWorkflowSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['hist_empr', 'hist_fili', 'hist_orde']
    pagination_class = PaginacaoResultados
    http_method_names = ['get']  # ReadOnly

    def get_queryset(self):
        banco = self.get_banco()
        empresa_id = self.request.headers.get("X-Empresa") or self.request.query_params.get('hist_empr')
        filial_id = self.request.headers.get("X-Filial") or self.request.query_params.get('hist_fili')
        
        qs = HistoricoWorkflow.objects.using(banco).all()
        if empresa_id:
            qs = qs.filter(hist_empr=empresa_id)
        if filial_id:
            qs = qs.filter(hist_fili=filial_id)
            
        return qs.order_by('hist_orde', 'hist_data')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Calculate times using service
        tempos_por_os = historico_service.calcular_tempos_por_os(queryset)
        
        # Format results using service
        detalhe_os, resumo_setor = historico_service.formatar_resultado_historico(tempos_por_os)
        
        # Pagination
        page = self.paginate_queryset(detalhe_os)
        if page is not None:
            return self.get_paginated_response({
                "detalhe_por_os": page,
                "resumo_setor_total": resumo_setor
            })
        
        empresa_id = self.request.headers.get("X-Empresa") or self.request.query_params.get('hist_empr')
        filial_id = self.request.headers.get("X-Filial") or self.request.query_params.get('hist_fili')
        
        return Response({
            "empresa": empresa_id,
            "filial": filial_id,
            "detalhe_por_os": detalhe_os,
            "resumo_setor_total": resumo_setor
        })
