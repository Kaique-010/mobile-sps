from .base import BaseListView
from Agricola.models import EstoqueFazenda

class EstoqueFazendaListView(BaseListView):
    model = EstoqueFazenda
    template_name = 'Agricola/estoque_fazenda_list.html'
    context_object_name = 'estoques_fazenda'
    empresa_field = 'estq_empr'
    filial_field = 'estq_fili'
    order_by_field = 'id'
