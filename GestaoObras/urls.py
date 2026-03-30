from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ObraEtapaViewSet,
    ObraLancamentoFinanceiroViewSet,
    ObraMaterialMovimentoViewSet,
    ObraProcessoViewSet,
    ObraViewSet,
)

router = DefaultRouter()
router.register("obras", ObraViewSet, basename="gestao-obras")
router.register("etapas", ObraEtapaViewSet, basename="gestao-obras-etapas")
router.register("movimentos-materiais", ObraMaterialMovimentoViewSet, basename="gestao-obras-movimentos")
router.register("lancamentos-financeiros", ObraLancamentoFinanceiroViewSet, basename="gestao-obras-financeiro")
router.register("processos", ObraProcessoViewSet, basename="gestao-obras-processos")

urlpatterns = [
    path("", include(router.urls)),
]
