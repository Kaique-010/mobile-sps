from django.urls import reverse_lazy
from .base import BaseDeleteView
from Agricola.models import AplicacaoInsumos

class AplicacaoInsumosDeleteView(BaseDeleteView):
    model = AplicacaoInsumos
    template_name = 'Agricola/aplicacao_insumos_confirm_delete.html'
    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:aplicacao_insumos_list', kwargs={'slug': self.kwargs['slug']})
    empresa_field = 'apli_empr'
    filial_field = 'apli_fili'
