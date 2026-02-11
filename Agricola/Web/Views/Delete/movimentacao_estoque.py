from django.urls import reverse_lazy
from .base import BaseDeleteView
from Agricola.models import MovimentacaoEstoque

class MovimentacaoEstoqueDeleteView(BaseDeleteView):
    model = MovimentacaoEstoque
    template_name = 'Agricola/movimentacao_estoque_confirm_delete.html'
    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:movimentacao_estoque_list', kwargs={'slug': self.kwargs['slug']})
    empresa_field = 'movi_estq_empr'
    filial_field = 'movi_estq_fili'
