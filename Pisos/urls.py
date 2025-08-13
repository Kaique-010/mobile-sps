from rest_framework.routers import DefaultRouter
from .views import (
    OrcamentopisosViewSet,
    PedidospisosViewSet,
    ItensorcapisosViewSet,
    ItenspedidospisosViewSet,
    ProdutosPisosViewSet
)

router = DefaultRouter()
router.register(r'orcamentos-pisos', OrcamentopisosViewSet, basename='orcamentos-pisos')
router.register(r'pedidos-pisos', PedidospisosViewSet, basename='pedidos-pisos')
router.register(r'itens-orcamentos-pisos', ItensorcapisosViewSet, basename='itens-orcamentos-pisos')
router.register(r'itens-pedidos-pisos', ItenspedidospisosViewSet, basename='itens-pedidos-pisos')
router.register(r'produtos-pisos', ProdutosPisosViewSet, basename='produtos-pisos')

urlpatterns = router.urls