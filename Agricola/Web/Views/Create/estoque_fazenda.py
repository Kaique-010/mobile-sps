from django.urls import reverse_lazy
from .base import BaseCreateView
from Agricola.models import EstoqueFazenda
from Agricola.Web.forms import EstoqueFazendaForm

class EstoqueFazendaCreateView(BaseCreateView):
    model = EstoqueFazenda
    form_class = EstoqueFazendaForm
    template_name = 'Agricola/estoque_fazenda_form.html'
    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:estoque_fazenda_list', kwargs={'slug': self.kwargs['slug']})
    empresa_field = 'estq_empr'
    filial_field = 'estq_fili'
