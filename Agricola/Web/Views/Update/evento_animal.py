from django.urls import reverse_lazy
from .base import BaseUpdateView
from Agricola.models import EventoAnimal
from Agricola.Web.forms import EventoAnimalForm

class EventoAnimalUpdateView(BaseUpdateView):
    model = EventoAnimal
    form_class = EventoAnimalForm
    template_name = 'Agricola/evento_animal_form.html'
    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:evento_animal_list', kwargs={'slug': self.kwargs['slug']})
    empresa_field = 'evnt_empr'
    filial_field = 'evnt_fili'
