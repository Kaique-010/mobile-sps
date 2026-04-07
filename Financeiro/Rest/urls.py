from rest_framework.routers import DefaultRouter
from Financeiro.Rest.views import OrcamentoViewSet, BaixasEmMassaViewSet

router = DefaultRouter()
router.register("orcamento", OrcamentoViewSet, basename="orcamento")
router.register("baixas-em-massa", BaixasEmMassaViewSet, basename="baixas-em-massa")

urlpatterns = router.urls
