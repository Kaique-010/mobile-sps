from django.urls import path
from .Views.createView import PedidoCreateView
from .Views.listView import PedidosListView
from .Views.detailView import PedidoDetailView
from .Views.printView import PedidoPrintView
from .Views.updateView import PedidoUpdateView
from .Views.dashboardView import PedidosDashboardView
from .Views.utils import autocomplete_clientes, autocomplete_vendedores, autocomplete_produtos, preco_produto
from .Views.emissao_nota import PedidoEmitirNFeView

app_name = "PedidosWeb"

urlpatterns = [
    path("", PedidosListView.as_view(), name="pedidos_listar"),
    path("dashboard/", PedidosDashboardView.as_view(), name="pedidos_dashboard"),
    path("criar/", PedidoCreateView.as_view(), name="pedido_criar"),
    path("<int:pk>/", PedidoDetailView.as_view(), name="pedido_detalhe"),
    path("<int:pk>/editar/", PedidoUpdateView.as_view(), name="pedido_editar"),
    path("<int:pk>/imprimir/", PedidoPrintView.as_view(), name="pedido_impressao"),
    path("por-cliente/", PedidosListView.as_view(), name="pedidos_por_cliente"),
    path("autocomplete/clientes/", autocomplete_clientes, name="autocomplete_clientes"),
    path("autocomplete/vendedores/", autocomplete_vendedores, name="autocomplete_vendedores"),
    path("autocomplete/produtos/", autocomplete_produtos, name="autocomplete_produtos"),
    path("preco/", preco_produto, name="preco_produto"),
    path("<int:pk>/emitir-nfe/", PedidoEmitirNFeView.as_view(), name="pedido_emitir_nfe"),
]