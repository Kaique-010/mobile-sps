from django.urls import reverse_lazy
from .base import BaseDeleteView
from Agricola.models import EstoqueFazenda

class EstoqueFazendaDeleteView(BaseDeleteView):
    model = EstoqueFazenda
    template_name = 'Agricola/estoque_fazenda_confirm_delete.html'
    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:estoque_fazenda_list', kwargs={'slug': self.kwargs['slug']})
    empresa_field = 'estq_empr'
    filial_field = 'estq_fili'
