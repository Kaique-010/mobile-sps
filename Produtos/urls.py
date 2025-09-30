from rest_framework.routers import DefaultRouter
from .views import ProdutoViewSet, UnidadeMedidaListView, TabelaPrecoMobileViewSet, ProdutosDetalhadosViewSet, EstoqueResumoView, MarcaListView
from django.urls import path

router = DefaultRouter()
router.register(r'produtos', ProdutoViewSet, basename='produtos')
router.register(r'tabelapreco', TabelaPrecoMobileViewSet, basename='tabelapreco')
router.register(r'produtosdetalhados', ProdutosDetalhadosViewSet, basename='produtosdetalhados')


urlpatterns = [
    path('unidadesmedida/', UnidadeMedidaListView.as_view(), name='unidade-list'),
    path('marcas/', MarcaListView.as_view(), name='marca-list'),
    path('estoqueresumo/', EstoqueResumoView.as_view(), name='estoque-resumo'),
    # URL para chave composta empresa/codigo
    path('produtos/<int:empresa>/<str:codigo>/', ProdutoViewSet.as_view({
        'get': 'retrieve',
        'put': 'update', 
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='produto-detail-composto'),
    # 
    path('tabelapreco/<str:chave_composta>/', TabelaPrecoMobileViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='tabelapreco-detail-composto'),
]

urlpatterns += router.urls
