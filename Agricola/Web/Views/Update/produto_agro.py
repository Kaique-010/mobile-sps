from django.urls import reverse_lazy
from .base import BaseUpdateView
from Agricola.models import ProdutoAgro, LoteProdutos
from Agricola.Web.forms import ProdutoAgroForm

class ProdutoAgroUpdateView(BaseUpdateView):
    model = ProdutoAgro
    form_class = ProdutoAgroForm
    template_name = 'Agricola/produto_agro_form.html'
    empresa_field = 'prod_empr_agro'
    filial_field = 'prod_fili_agro'

    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:produto_agro_list', kwargs={'slug': self.kwargs['slug']})

    def get_context_data(self, **kwargs):
        from core.utils import get_licenca_db_config
        
        context = super().get_context_data(**kwargs)
        if self.object:
            banco = get_licenca_db_config(self.request) or 'default'
            db_name = banco if isinstance(banco, str) else banco.get('db_name', 'default')
            
            # Assumes lote_prod stores the PK of ProdutoAgro
            context['lotes'] = LoteProdutos.objects.using(db_name).filter(lote_prod=self.object.pk)
        return context
