from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    ObraViewSet,
    ObraEtapaViewSet,
    ObraMaterialMovimentoViewSet,
    ObraLancamentoFinanceiroViewSet,
    ObraProcessoViewSet,
)
from .autocompletes import autocomplete_entidades

router = DefaultRouter()
router.register("obras", ObraViewSet, basename="gestao-obras")
router.register("etapas", ObraEtapaViewSet, basename="gestao-obras-etapas")
router.register("movimentos-materiais", ObraMaterialMovimentoViewSet, basename="gestao-obras-movimentos")
router.register("lancamentos-financeiros", ObraLancamentoFinanceiroViewSet, basename="gestao-obras-financeiro")
router.register("processos", ObraProcessoViewSet, basename="gestao-obras-processos")

urlpatterns = router.urls + [
    path("autocompletes/entidades/", autocomplete_entidades, name="gestaoobras-autocomplete-entidades"),
]
