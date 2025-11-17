from django.urls import path
from .Views.listView import SaidaListView
from .Views.createView import SaidaCreateView
from .Views.detailView import SaidaDetailView
from .Views.updateView import SaidaUpdateView
from .Views.utils import autocomplete_clientes, autocomplete_produtos

app_name = "SaidasWeb"

urlpatterns = [
    path("", SaidaListView.as_view(), name="saidas_listar"),
    path("criar/", SaidaCreateView.as_view(), name="saidas_criar"),
    path("<int:pk>/", SaidaDetailView.as_view(), name="saidas_detalhe"),
    path("<int:pk>/editar/", SaidaUpdateView.as_view(), name="saidas_editar"),
    path("autocomplete/clientes/", autocomplete_clientes, name="autocomplete_clientes"),
    path("autocomplete/produtos/", autocomplete_produtos, name="autocomplete_produtos"),
]