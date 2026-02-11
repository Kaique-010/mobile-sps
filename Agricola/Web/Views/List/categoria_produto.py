from .base import BaseListView
from Agricola.models import CategoriaProduto

class CategoriaProdutoListView(BaseListView):
    model = CategoriaProduto
    template_name = 'Agricola/categoria_produto_list.html'
    context_object_name = 'categorias_produtos'
    empresa_field = None
    filial_field = None
    order_by_field = 'cate_nome'
