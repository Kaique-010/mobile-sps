from django.views.generic import DeleteView
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.models import Bombas

class BombasDeleteView(DeleteView):
    model = Bombas
    template_name = 'transportes/bombas_delete.html'

    def get_success_url(self):
        return reverse('transportes:bombas_lista', kwargs={'slug': self.kwargs['slug']})

    def _get_banco(self):
        slug = self.kwargs.get('slug')
        return get_db_from_slug(slug) if slug else get_licenca_db_config(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')
        return context

    def get_object(self, queryset=None):
        banco = self._get_banco()
        empresa_id = self.request.session.get('empresa_id')
        bomba_codigo = self.kwargs.get('bomb_codi')
        
        return get_object_or_404(
            Bombas.objects.using(banco), 
            bomb_empr=empresa_id, 
            bomb_codi=bomba_codigo
        )

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        banco = self._get_banco()
        empresa_id = self.request.session.get('empresa_id')
        bomba_codigo = self.kwargs.get('bomb_codi')
        Bombas.objects.using(banco).filter(
            bomb_empr=empresa_id, 
            bomb_codi=bomba_codigo  
        ).delete()
        
        messages.success(request, 'Bomba excluída com sucesso!')
        return redirect(self.get_success_url())
