from rest_framework.routers import DefaultRouter
from Financeiro.Rest.views import OrcamentoViewSet

router = DefaultRouter()
router.register("orcamento", OrcamentoViewSet, basename="orcamento")

urlpatterns = router.urls