from django.urls import path
from .Views.listar import OsListView
from . import web_views
from .Views.criar import OsCreateView
from .Views.detalhes import OsDetailView
from .Views.update import OsUpdateView
from .Views.imprimir import OsPrintView

app_name = "OsWeb"

urlpatterns = [
    path("", OsListView.as_view(), name="os_listar"),
    path("criar/", OsCreateView.as_view(), name="os_criar"),
    path("<int:pk>/", OsDetailView.as_view(), name="os_detalhe"),
    path("<int:pk>/editar/", OsUpdateView.as_view(), name="os_editar"),
    path("<int:pk>/imprimir/", OsPrintView.as_view(), name="os_impressao"),
    path("dashboard/", web_views.OsDashboardView.as_view(), name="os_dashboard"),
    # Alias compatível com templates existentes
    path("por-cliente/", OsListView.as_view(), name="os_por_cliente"),
    # Endpoints de autocomplete
    path("autocomplete/clientes/", web_views.autocomplete_clientes, name="autocomplete_clientes"),
    path("autocomplete/vendedores/", web_views.autocomplete_vendedores, name="autocomplete_vendedores"),
    path("autocomplete/produtos/", web_views.autocomplete_produtos, name="autocomplete_produtos"),
    path("autocomplete/atendentes/", web_views.autocomplete_atendentes, name="autocomplete_atendentes"),
    path("autocomplete/status/", web_views.autocomplete_status_os, name="autocomplete_status"),
    path("preco/", web_views.preco_produto, name="preco_produto"),
]