from django.urls import reverse_lazy
from .base import BaseDeleteView
from Agricola.models import Animal

class AnimalDeleteView(BaseDeleteView):
    model = Animal
    template_name = 'Agricola/animal_confirm_delete.html'
    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:animal_list', kwargs={'slug': self.kwargs['slug']})
    empresa_field = 'anim_empr'
    filial_field = 'anim_fili'
