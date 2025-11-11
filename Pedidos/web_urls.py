from django.urls import path
from . import web_views

app_name = "PedidosWeb"

urlpatterns = [
    path("", web_views.PedidosListView.as_view(), name="pedidos_listar"),
    path("criar/", web_views.PedidoCreateView.as_view(), name="pedido_criar"),
    path("<int:pk>/", web_views.PedidoDetailView.as_view(), name="pedido_detalhe"),
    path("<int:pk>/imprimir/", web_views.PedidoPrintView.as_view(), name="pedido_impressao"),
    # Alias compatível com templates existentes
    path("por-cliente/", web_views.PedidosListView.as_view(), name="pedidos_por_cliente"),
]