from django.urls import reverse_lazy
from django.shortcuts import redirect
from .base import BaseCreateView
from Agricola.models import ProdutoAgro
from Agricola.Web.forms import ProdutoAgroForm
from Agricola.service.cadastros_service import CadastrosDomainService

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
        
        # Obtém empresa e filial do contexto da view (setados em form_valid ou via mixin)
        # O BaseCreateView geralmente seta self.object com os campos preenchidos
        # mas aqui estamos pegando de self.object antes de salvar?
        # Sim, o BaseCreateView padrão seta self.object = form.save(commit=False).
        # E o método form_valid do BaseCreateView chama execute_create.
        
        empresa = getattr(self.object, 'prod_empr_agro')
        filial = getattr(self.object, 'prod_fili_agro')
        
        data['prod_empr_agro'] = empresa
        data['prod_fili_agro'] = filial
        
        return CadastrosDomainService.cadastrar_produto(
            empresa=empresa,
            filial=filial,
            dados=data,
            using=db_name
        )
