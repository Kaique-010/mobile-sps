from django.urls import reverse_lazy
from .base import BaseCreateView
from Agricola.models import HistoricoMovimentacao
from Agricola.Web.forms import HistoricoMovimentacaoForm

class HistoricoMovimentacaoCreateView(BaseCreateView):
    model = HistoricoMovimentacao
    form_class = HistoricoMovimentacaoForm
    template_name = 'Agricola/historico_movimentacao_form.html'
    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:historico_movimentacao_list', kwargs={'slug': self.kwargs['slug']})
    empresa_field = 'hist_empr'
    filial_field = 'hist_fili'
