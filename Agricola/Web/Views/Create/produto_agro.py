from django.urls import reverse_lazy
from .base import BaseCreateView
from Agricola.models import ProdutoAgro
from Agricola.Web.forms import ProdutoAgroForm

class ProdutoAgroCreateView(BaseCreateView):
    model = ProdutoAgro
    form_class = ProdutoAgroForm
    template_name = 'Agricola/produto_agro_form.html'
    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:produto_agro_list', kwargs={'slug': self.kwargs['slug']})
    empresa_field = 'prod_empr_agro'
    filial_field = 'prod_fili_agro'
