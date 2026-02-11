from .base import BaseListView
from Agricola.models import MovimentacaoEstoque

class MovimentacaoEstoqueListView(BaseListView):
    model = MovimentacaoEstoque
    template_name = 'Agricola/movimentacao_estoque_list.html'
    context_object_name = 'movimentacoes_estoque'
    empresa_field = 'movi_estq_empr'
    filial_field = 'movi_estq_fili'
    order_by_field = '-movi_estq_data'
