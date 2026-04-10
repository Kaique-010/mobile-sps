from rest_framework.routers import DefaultRouter
from .viewsets import RegraComissaoViewSet, LancamentoComissaoViewSet, PagamentoComissaoViewSet

router = DefaultRouter()
router.register(r"regras", RegraComissaoViewSet, basename="comissoes-regras")
router.register(r"lancamentos", LancamentoComissaoViewSet, basename="comissoes-lancamentos")
router.register(r"pagamentos", PagamentoComissaoViewSet, basename="comissoes-pagamentos")

urlpatterns = router.urls
