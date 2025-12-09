from django.urls import path
from .Views.listar import OsListView
from .Views.criar import OsCreateView
from .Views.update import OsUpdateView
from .Views.imprimir import OsPrintView
from .Views import web_views



app_name = "OsExterna"

urlpatterns = [
    path("", OsListView.as_view(), name="os_listar"),
    path("criar/", OsCreateView.as_view(), name="os_criar"),
    path("<int:pk>/editar/", OsUpdateView.as_view(), name="os_editar"),
    path("<int:pk>/imprimir/", OsPrintView.as_view(), name="os_impressao"),
   
    # Endpoints de autocomplete
    path("autocomplete/clientes/", web_views.autocomplete_clientes, name="autocomplete_clientes"),
    path("autocomplete/responsaveis/", web_views.autocomplete_responsaveis, name="autocomplete_responsaveis"),
    path("autocomplete/produtos/", web_views.autocomplete_produtos, name="autocomplete_produtos"),
    path("preco/", web_views.preco_produto, name="preco_produto"),
]