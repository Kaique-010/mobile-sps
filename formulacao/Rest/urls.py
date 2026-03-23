from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import FormulaViewSet, OrdemProducaoViewSet

app_name = "FormulacaoRest"

router = DefaultRouter()
router.register(r"formulas", FormulaViewSet, basename="formulas")
router.register(r"ordens-producao", OrdemProducaoViewSet, basename="ordens_producao")

urlpatterns = [
    path("", include(router.urls)),
]
