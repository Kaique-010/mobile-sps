from django.urls import path
from . import web_views

app_name = "OsWeb"

urlpatterns = [
    path("", web_views.OsListView.as_view(), name="os_listar"),
    path("criar/", web_views.OsCreateView.as_view(), name="os_criar"),
    path("<int:pk>/", web_views.OsDetailView.as_view(), name="os_detalhe"),
    path("<int:pk>/editar/", web_views.OsUpdateView.as_view(), name="os_editar"),
    path("<int:pk>/imprimir/", web_views.OsPrintView.as_view(), name="os_impressao"),
    # Alias compatível com templates existentes
    path("por-cliente/", web_views.OsListView.as_view(), name="os_por_cliente"),
    # Endpoints de autocomplete
    path("autocomplete/clientes/", web_views.autocomplete_clientes, name="autocomplete_clientes"),
    path("autocomplete/vendedores/", web_views.autocomplete_vendedores, name="autocomplete_vendedores"),
    path("autocomplete/produtos/", web_views.autocomplete_produtos, name="autocomplete_produtos"),
    path("preco/", web_views.preco_produto, name="preco_produto"),
]