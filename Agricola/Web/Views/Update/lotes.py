from django.urls import reverse_lazy
from .base import BaseUpdateView
from Agricola.models import ProdutoAgro, LoteProdutos
from Agricola.Web.forms import ProdutoAgroForm, LoteProdutosForm
from django.shortcuts import render

class LoteProdutosUpdateView(BaseUpdateView):
    model = LoteProdutos
    form_class = LoteProdutosForm
    template_name = 'Agricola/lote_produtos_form.html'
    empresa_field = 'lote_empr'
    filial_field = 'lote_fili'

    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:lote_produtos_list', kwargs={'slug': self.kwargs['slug']})

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return ['Agricola/parciais/lote_form.html']
        return [self.template_name]

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('HX-Request'):
            from core.utils import get_licenca_db_config
            banco = get_licenca_db_config(self.request) or 'default'
            db_name = banco if isinstance(banco, str) else banco.get('db_name', 'default')
            
            # Filter by the product of the current lote
            lotes = LoteProdutos.objects.using(db_name).filter(lote_prod=self.object.lote_prod)
            
            return render(self.request, 'Agricola/parciais/lote_list.html', {
                'lotes': lotes,
                'slug': self.kwargs.get('slug')
            })
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        from core.utils import get_licenca_db_config
        
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')
        
        if self.object:
            banco = get_licenca_db_config(self.request) or 'default'
            db_name = banco if isinstance(banco, str) else banco.get('db_name', 'default')
            
            # Correcting the filter to show siblings (lotes of the same product)
            # Assuming lote_prod is the FK to ProdutoAgro
            context['lotes'] = LoteProdutos.objects.using(db_name).filter(lote_prod=self.object.lote_prod)
        return context
