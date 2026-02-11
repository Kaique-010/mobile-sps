from django.urls import reverse_lazy
from .base import BaseCreateView
from Agricola.models import EventoAnimal
from Agricola.Web.forms import EventoAnimalForm

from core.utils import get_licenca_db_config

class EventoAnimalCreateView(BaseCreateView):
    model = EventoAnimal
    form_class = EventoAnimalForm
    template_name = 'Agricola/evento_animal_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        banco = get_licenca_db_config(self.request) or 'default'
        db_name = banco if isinstance(banco, str) else banco.get('db_name', 'default')
        kwargs['db_alias'] = db_name
        return kwargs

    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:evento_animal_list', kwargs={'slug': self.kwargs['slug']})
    empresa_field = 'evnt_empr'
    filial_field = 'evnt_fili'
