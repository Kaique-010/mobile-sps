from .base import BaseListView
from Agricola.models import HistoricoMovimentacao

class HistoricoMovimentacaoListView(BaseListView):
    model = HistoricoMovimentacao
    template_name = 'Agricola/historico_movimentacao_list.html'
    context_object_name = 'historicos_movimentacao'
    empresa_field = 'hist_empr'
    filial_field = 'hist_fili'
    order_by_field = '-hist_data'
