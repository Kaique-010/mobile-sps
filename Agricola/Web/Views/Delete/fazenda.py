from django.urls import reverse_lazy
from .base import BaseDeleteView
from Agricola.models import Fazenda

class FazendaDeleteView(BaseDeleteView):
    model = Fazenda
    template_name = 'Agricola/fazenda_confirm_delete.html'
    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:fazenda_list', kwargs={'slug': self.kwargs['slug']})
    empresa_field = 'faze_empr'
    filial_field = 'faze_fili'
