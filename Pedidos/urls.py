# urls.py
from email.mime import base
from django.urls import path
from rest_framework.routers import DefaultRouter
from .rest.views import PedidoVendaViewSet
from .rest.views_dashboard import PedidosGeralViewSet
from .rest.views_financeiro import (
    GerarTitulosPedidoView,
    RemoverTitulosPedidoView,
    ConsultarTitulosPedidoView,
    AtualizarTituloPedidoView,
    RelatorioFinanceiroPedidoView
)

router = DefaultRouter()
router.register(r'pedidos', PedidoVendaViewSet, basename='pedidos')
router.register(r'pedidos-geral', PedidosGeralViewSet, basename='pedidos-geral')

# URLs customizadas para chave composta
custom_patterns = [
    path('pedidos/<int:empresa>/<int:filial>/<int:numero>/', 
         PedidoVendaViewSet.as_view({
             'get': 'retrieve',
             'put': 'update', 
             'patch': 'partial_update',
             'delete': 'destroy'
         }), name='pedido-detail-composto'),
    path('pedidos/<int:empresa>/<int:filial>/<int:numero>/cancelar_pedido/', 
         PedidoVendaViewSet.as_view({
             'post': 'cancelar_pedido'
         }), name='pedido-cancelar-composto'),
]

# URLs para funcionalidades financeiras
urlpatterns = custom_patterns + [
    path('gerar-titulos-pedido/', GerarTitulosPedidoView.as_view(), name='gerar-titulos-pedido'),
    path('remover-titulos-pedido/', RemoverTitulosPedidoView.as_view(), name='remover-titulos-pedido'),
    path('consultar-titulos-pedido/<int:pedi_nume>/', ConsultarTitulosPedidoView.as_view(), name='consultar-titulos-pedido'),
    path('atualizar-titulo-pedido/', AtualizarTituloPedidoView.as_view(), name='atualizar-titulo-pedido'),
    path('relatorio-financeiro-pedido/', RelatorioFinanceiroPedidoView.as_view(), name='relatorio-financeiro-pedido'),
]

urlpatterns += router.urls
