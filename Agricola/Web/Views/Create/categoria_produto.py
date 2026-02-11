from django.urls import reverse_lazy
from .base import BaseCreateView
from Agricola.models import CategoriaProduto
from Agricola.Web.forms import CategoriaProdutoForm

class CategoriaProdutoCreateView(BaseCreateView):
    model = CategoriaProduto
    form_class = CategoriaProdutoForm
    template_name = 'Agricola/categoria_produto_form.html'
    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:categoria_produto_list', kwargs={'slug': self.kwargs['slug']})
    # Sem campos de empresa/filial
