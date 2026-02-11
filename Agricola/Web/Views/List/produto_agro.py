from .base import BaseListView
from Agricola.models import ProdutoAgro

class ProdutoAgroListView(BaseListView):
    model = ProdutoAgro
    template_name = 'Agricola/produto_agro_list.html'
    context_object_name = 'produtos_agro'
    empresa_field = 'prod_empr_agro'
    filial_field = 'prod_fili_agro'
    order_by_field = 'prod_nome_agro'
