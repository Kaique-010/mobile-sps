from django.urls import reverse_lazy
from .base import BaseDeleteView
from Agricola.models import Talhao

class TalhaoDeleteView(BaseDeleteView):
    model = Talhao
    template_name = 'Agricola/talhao_confirm_delete.html'
    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:talhao_list', kwargs={'slug': self.kwargs['slug']})
    empresa_field = 'talh_empr'
    filial_field = 'talh_fili'
