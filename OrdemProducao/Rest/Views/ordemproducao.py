from rest_framework.decorators import action
from rest_framework.response import Response

from ...models import Ordemproducao
from ...services import OrdemProducaoService
from ..serializers import OrdemproducaoSerializer
from .base import BaseMultiDBModelViewSet


class OrdemproducaoViewSet(BaseMultiDBModelViewSet):
    queryset = Ordemproducao.objects.all()
    serializer_class = OrdemproducaoSerializer
    filterset_fields = ['orpr_tipo', 'orpr_codi', 'orpr_entr', 'orpr_clie', 'orpr_stat']
    search_fields = ['orpr_tipo', 'orpr_codi', 'orpr_clie', 'orpr_nuca', 'cliente_nome']
    ordering_fields = ['orpr_tipo', 'orpr_codi', 'orpr_entr', 'orpr_clie', 'orpr_prev']
    ordering = ['-orpr_codi']

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        return Response(OrdemProducaoService.dashboard(using=self.get_banco()))

    @action(detail=False, methods=["get"], url_path="dashboard-detalhado")
    def dashboard_detalhado(self, request, slug=None):
        filtros = {
            "data_ini": request.query_params.get("data_ini") or None,
            "data_fim": request.query_params.get("data_fim") or None,
            "empr": request.query_params.get("empr") or None,
            "fili": request.query_params.get("fili") or None,
            "tipo": request.query_params.get("tipo") or None,
            "status": request.query_params.get("status") or None,
        }
        return Response(OrdemProducaoService.dashboard_detalhado(using=self.get_banco(), filtros=filtros))

    @action(detail=True, methods=['post'])
    def iniciar_producao(self, request, pk=None):
        OrdemProducaoService.iniciar_producao(ordem=self.get_object(), using=self.get_banco())
        return Response({'message': 'Produção iniciada com sucesso'})

    @action(detail=True, methods=['post'])
    def finalizar_ordem(self, request, pk=None):
        OrdemProducaoService.finalizar_ordem(ordem=self.get_object(), using=self.get_banco())
        return Response({'message': 'Ordem finalizada com sucesso'})
