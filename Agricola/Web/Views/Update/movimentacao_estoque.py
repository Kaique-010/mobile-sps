from django.urls import reverse_lazy
from .base import BaseUpdateView
from Agricola.models import MovimentacaoEstoque
from Agricola.Web.forms import MovimentacaoEstoqueForm

class MovimentacaoEstoqueUpdateView(BaseUpdateView):
    model = MovimentacaoEstoque
    form_class = MovimentacaoEstoqueForm
    template_name = 'Agricola/movimentacao_estoque_form.html'
    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:movimentacao_estoque_list', kwargs={'slug': self.kwargs['slug']})
    empresa_field = 'movi_estq_empr'
    filial_field = 'movi_estq_fili'
