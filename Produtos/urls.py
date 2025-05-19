from rest_framework.routers import DefaultRouter
from .views import ProdutoViewSet, UnidadeMedidaListView, TabelaPrecoMobileViewSet
from django.urls import path

router = DefaultRouter()
router.register(r'produtos', ProdutoViewSet, basename='produtos')
router.register(r'tabelapreco', TabelaPrecoMobileViewSet, basename='tabelapreco')

urlpatterns = [
    path('unidadesmedida/', UnidadeMedidaListView.as_view(), name='unidade-list'),
]

urlpatterns += router.urls
