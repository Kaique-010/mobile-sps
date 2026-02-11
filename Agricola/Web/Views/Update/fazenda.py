from django.urls import reverse_lazy
from .base import BaseUpdateView
from Agricola.models import Fazenda
from Agricola.Web.forms import FazendaForm

class FazendaUpdateView(BaseUpdateView):
    model = Fazenda
    form_class = FazendaForm
    template_name = 'Agricola/fazenda_form.html'
    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:fazenda_list', kwargs={'slug': self.kwargs['slug']})
    empresa_field = 'faze_empr'
    filial_field = 'faze_fili'
