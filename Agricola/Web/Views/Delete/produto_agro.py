from django.urls import reverse_lazy
from .base import BaseDeleteView
from Agricola.models import ProdutoAgro

class ProdutoAgroDeleteView(BaseDeleteView):
    model = ProdutoAgro
    template_name = 'Agricola/produto_agro_confirm_delete.html'
    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:produto_agro_list', kwargs={'slug': self.kwargs['slug']})
    empresa_field = 'prod_empr_agro'
    filial_field = 'prod_fili_agro'
