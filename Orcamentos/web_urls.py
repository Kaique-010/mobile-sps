from django.urls import path
from . import web_views

app_name = "OrcamentosWeb"

urlpatterns = [
    path("", web_views.OrcamentosListView.as_view(), name="orcamentos_listar"),
    path("criar/", web_views.OrcamentoCreateView.as_view(), name="orcamento_criar"),
    path("<int:pk>/", web_views.OrcamentoDetailView.as_view(), name="orcamento_detalhe"),
    path("<int:pk>/editar/", web_views.OrcamentoUpdateView.as_view(), name="orcamento_editar"),
    path("<int:pk>/imprimir/", web_views.OrcamentoPrintView.as_view(), name="orcamento_impressao"),
    # Autocomplete endpoints
    path("autocomplete/clientes/", web_views.autocomplete_clientes, name="autocomplete_clientes"),
    path("autocomplete/vendedores/", web_views.autocomplete_vendedores, name="autocomplete_vendedores"),
    path("autocomplete/produtos/", web_views.autocomplete_produtos, name="autocomplete_produtos"),
    path("preco/", web_views.preco_produto, name="preco_produto"),
]