from rest_framework.routers import DefaultRouter
from .views import (
    OrcamentopisosViewSet,
    PedidospisosViewSet,
    ItensorcapisosViewSet,
    ItenspedidospisosViewSet,
    ProdutosPisosViewSet
)
from django.urls import path

router = DefaultRouter()
router.register(r'orcamentos-pisos', OrcamentopisosViewSet, basename='orcamentos-pisos')
router.register(r'pedidos-pisos', PedidospisosViewSet, basename='pedidos-pisos')
router.register(r'itens-orcamentos-pisos', ItensorcapisosViewSet, basename='itens-orcamentos-pisos')
router.register(r'itens-pedidos-pisos', ItenspedidospisosViewSet, basename='itens-pedidos-pisos')
router.register(r'produtos-pisos', ProdutosPisosViewSet, basename='produtos-pisos')

# URLs customizadas para chave composta
custom_patterns = [
    path('orcamentos-pisos/<int:empresa>/<int:filial>/<int:numero>/', 
         OrcamentopisosViewSet.as_view({
             'get': 'retrieve',
             'put': 'update', 
             'patch': 'partial_update',
             'delete': 'destroy'
         }), name='orcamento-detail-composto'),

path('orcamentos-pisos/<int:empresa>/<int:filial>/<int:numero>/exportar-pedido/',
         OrcamentopisosViewSet.as_view({'post': 'exportar_pedido'}),
         name='exportar-pedido')
]
urlpatterns = custom_patterns + router.urls