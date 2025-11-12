from django.urls import path
from . import web_views

app_name = "PedidosWeb"

urlpatterns = [
    path("", web_views.PedidosListView.as_view(), name="pedidos_listar"),
    path("criar/", web_views.PedidoCreateView.as_view(), name="pedido_criar"),
    path("<int:pk>/", web_views.PedidoDetailView.as_view(), name="pedido_detalhe"),
    path("<int:pk>/editar/", web_views.PedidoUpdateView.as_view(), name="pedido_editar"),
    path("<int:pk>/imprimir/", web_views.PedidoPrintView.as_view(), name="pedido_impressao"),
    # Alias compatível com templates existentes
    path("por-cliente/", web_views.PedidosListView.as_view(), name="pedidos_por_cliente"),
    # Endpoints de autocomplete
    path("autocomplete/clientes/", web_views.autocomplete_clientes, name="autocomplete_clientes"),
    path("autocomplete/vendedores/", web_views.autocomplete_vendedores, name="autocomplete_vendedores"),
    path("autocomplete/produtos/", web_views.autocomplete_produtos, name="autocomplete_produtos"),
    path("preco/", web_views.preco_produto, name="preco_produto"),
]