from django.urls import reverse_lazy
from .base import BaseUpdateView
from Agricola.models import AplicacaoInsumos
from Agricola.Web.forms import AplicacaoInsumosForm

class AplicacaoInsumosUpdateView(BaseUpdateView):
    model = AplicacaoInsumos
    form_class = AplicacaoInsumosForm
    template_name = 'Agricola/aplicacao_insumos_form.html'
    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:aplicacao_insumos_list', kwargs={'slug': self.kwargs['slug']})
    empresa_field = 'apli_empr'
    filial_field = 'apli_fili'
