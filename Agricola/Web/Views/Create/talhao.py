from django.urls import reverse_lazy
from .base import BaseCreateView
from Agricola.models import Talhao
from Agricola.Web.forms import TalhaoForm

class TalhaoCreateView(BaseCreateView):
    model = Talhao
    form_class = TalhaoForm
    template_name = 'Agricola/talhao_form.html'
    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:talhao_list', kwargs={'slug': self.kwargs['slug']})
    empresa_field = 'talh_empr'
    filial_field = 'talh_fili'

    
    