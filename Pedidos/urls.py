# urls.py
from email.mime import base
from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import PedidoVendaViewSet
from .views_dashboard import PedidosGeralViewSet
from .views_financeiro import (
    GerarTitulosPedidoView,
    RemoverTitulosPedidoView,
    ConsultarTitulosPedidoView,
    AtualizarTituloPedidoView,
    RelatorioFinanceiroPedidoView
)

router = DefaultRouter()
router.register(r'pedidos', PedidoVendaViewSet, basename='pedidos')
router.register(r'pedidos-geral', PedidosGeralViewSet, basename='pedidos-geral')

# URLs para funcionalidades financeiras
urlpatterns = [
    path('gerar-titulos-pedido/', GerarTitulosPedidoView.as_view(), name='gerar-titulos-pedido'),
    path('remover-titulos-pedido/', RemoverTitulosPedidoView.as_view(), name='remover-titulos-pedido'),
    path('consultar-titulos-pedido/<int:pedi_nume>/', ConsultarTitulosPedidoView.as_view(), name='consultar-titulos-pedido'),
    path('atualizar-titulo-pedido/', AtualizarTituloPedidoView.as_view(), name='atualizar-titulo-pedido'),
    path('relatorio-financeiro-pedido/', RelatorioFinanceiroPedidoView.as_view(), name='relatorio-financeiro-pedido'),
]

urlpatterns += router.urls
