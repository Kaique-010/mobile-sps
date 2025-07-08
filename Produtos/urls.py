from rest_framework.routers import DefaultRouter
from .views import ProdutoViewSet, UnidadeMedidaListView, TabelaPrecoMobileViewSet, ProdutosDetalhadosViewSet
from django.urls import path

router = DefaultRouter()
router.register(r'produtos', ProdutoViewSet, basename='produtos')
router.register(r'tabelapreco', TabelaPrecoMobileViewSet, basename='tabelapreco')
router.register(r'produtosdetalhados', ProdutosDetalhadosViewSet, basename='produtosdetalhados')

urlpatterns = [
    path('unidadesmedida/', UnidadeMedidaListView.as_view(), name='unidade-list'),

]

urlpatterns += router.urls
