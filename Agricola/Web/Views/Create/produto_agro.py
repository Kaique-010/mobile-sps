from django.urls import reverse_lazy
from django.shortcuts import redirect
from .base import BaseCreateView
from Agricola.models import ProdutoAgro
from Agricola.Web.forms import ProdutoAgroForm
from Agricola.service.produto_agro_service import ProdutoAgroService

class ProdutoAgroCreateView(BaseCreateView):
    model = ProdutoAgro
    form_class = ProdutoAgroForm
    template_name = 'Agricola/produto_agro_form.html'
    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:produto_agro_list', kwargs={'slug': self.kwargs['slug']})
    empresa_field = 'prod_empr_agro'
    filial_field = 'prod_fili_agro'
    
    def execute_create(self, form, db_name):
        data = form.cleaned_data.copy()
        data['prod_empr_agro'] = getattr(self.object, 'prod_empr_agro')
        data['prod_fili_agro'] = getattr(self.object, 'prod_fili_agro')
        
        return ProdutoAgroService.criar_produto(
            data=data,
            using=db_name
        )
