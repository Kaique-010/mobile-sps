from django.urls import reverse_lazy
from .base import BaseDeleteView
from Agricola.models import HistoricoMovimentacao

class HistoricoMovimentacaoDeleteView(BaseDeleteView):
    model = HistoricoMovimentacao
    template_name = 'Agricola/historico_movimentacao_confirm_delete.html'
    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:historico_movimentacao_list', kwargs={'slug': self.kwargs['slug']})
    empresa_field = 'hist_empr'
    filial_field = 'hist_fili'
