from django.urls import reverse_lazy
from .base import BaseDeleteView
from Agricola.models import LoteProdutos
from django.shortcuts import render
from django.http import HttpResponseRedirect

class LoteProdutosDeleteView(BaseDeleteView):
    model = LoteProdutos
    template_name = 'Agricola/lote_produtos_confirm_delete.html'
    empresa_field = 'lote_empr'
    filial_field = 'lote_fili'

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return ['Agricola/parciais/lote_confirm_delete.html']
        return [self.template_name]

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        
        # Save parent ID to refresh list
        lote_prod_id = self.object.lote_prod
        
        self.object.delete()
        
        if self.request.headers.get('HX-Request'):
            from core.utils import get_licenca_db_config
            banco = get_licenca_db_config(self.request) or 'default'
            db_name = banco if isinstance(banco, str) else banco.get('db_name', 'default')
            
            lotes = LoteProdutos.objects.using(db_name).filter(lote_prod=lote_prod_id)
            
            return render(self.request, 'Agricola/parciais/lote_list.html', {
                'lotes': lotes,
                'slug': self.kwargs.get('slug')
            })
            
        return HttpResponseRedirect(success_url)

    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:lote_produtos_list', kwargs={'slug': self.kwargs['slug']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')
        return context
