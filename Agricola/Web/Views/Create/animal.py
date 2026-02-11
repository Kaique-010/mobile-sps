from django.urls import reverse_lazy
from .base import BaseCreateView
from Agricola.models import Animal
from Agricola.Web.forms import AnimalForm

class AnimalCreateView(BaseCreateView):
    model = Animal
    form_class = AnimalForm
    template_name = 'Agricola/animal_form.html'
    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:animal_list', kwargs={'slug': self.kwargs['slug']})
    empresa_field = 'anim_empr'
    filial_field = 'anim_fili'
