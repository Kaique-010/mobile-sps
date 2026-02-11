from django.urls import reverse_lazy
from .base import BaseDeleteView
from Agricola.models import CategoriaProduto

class CategoriaProdutoDeleteView(BaseDeleteView):
    model = CategoriaProduto
    template_name = 'Agricola/categoria_produto_confirm_delete.html'
    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:categoria_produto_list', kwargs={'slug': self.kwargs['slug']})
