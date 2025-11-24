from django.urls import path
from .Views.listView import OrcamentosListView
from .Views.createView import OrcamentoCreateView
from .Views.detailView import OrcamentoDetailView
from .Views.updateView import OrcamentoUpdateView
from .Views.printView import OrcamentoPrintView
from .Views.utils import autocomplete_clientes, autocomplete_vendedores, autocomplete_produtos, preco_produto
from .Views.trans_pedido import transformar_em_pedido_web

app_name = "OrcamentosWeb"

urlpatterns = [
    path("", OrcamentosListView.as_view(), name="orcamentos_listar"),
    path("criar/", OrcamentoCreateView.as_view(), name="orcamento_criar"),
    path("<int:pk>/", OrcamentoDetailView.as_view(), name="orcamento_detalhe"),
    path("<int:pk>/editar/", OrcamentoUpdateView.as_view(), name="orcamento_editar"),
    path("<int:pk>/imprimir/", OrcamentoPrintView.as_view(), name="orcamento_impressao"),
    path("<int:pk>/transformar/", transformar_em_pedido_web, name="orcamento_transformar"),
    path("autocomplete/clientes/", autocomplete_clientes, name="autocomplete_clientes"),
    path("autocomplete/vendedores/", autocomplete_vendedores, name="autocomplete_vendedores"),
    path("autocomplete/produtos/", autocomplete_produtos, name="autocomplete_produtos"),
    path("preco/", preco_produto, name="preco_produto"),
]
