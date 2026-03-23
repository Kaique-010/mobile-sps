from django.urls import path
from .Views.listView import EntradaListView
from .Views.createView import EntradaCreateView, EntradaLoteView
from .Views.detailView import EntradaDetailView
from .Views.updateView import EntradaUpdateView
from .Views.utils import autocomplete_clientes, autocomplete_produtos, lotes_produto

app_name = "EntradasWeb"

urlpatterns = [
    path("", EntradaListView.as_view(), name="entradas_listar"),
    path("criar/", EntradaCreateView.as_view(), name="entradas_criar"),
    path("lote/", EntradaLoteView.as_view(), name="entradas_lote"),
    path("lotes/produto/", lotes_produto, name="lotes_produto"),
    path("<int:pk>/", EntradaDetailView.as_view(), name="entradas_detalhe"),
    path("<int:pk>/editar/", EntradaUpdateView.as_view(), name="entradas_editar"),
    path("autocomplete/clientes/", autocomplete_clientes, name="autocomplete_clientes"),
    path("autocomplete/produtos/", autocomplete_produtos, name="autocomplete_produtos"),
]
