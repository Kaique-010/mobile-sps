from django.urls import reverse_lazy
from .base import BaseDeleteView
from Agricola.models import EventoAnimal

class EventoAnimalDeleteView(BaseDeleteView):
    model = EventoAnimal
    template_name = 'Agricola/evento_animal_confirm_delete.html'
    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:evento_animal_list', kwargs={'slug': self.kwargs['slug']})
    empresa_field = 'evnt_empr'
    filial_field = 'evnt_fili'
