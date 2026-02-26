from django.views.generic import DeleteView
from django.shortcuts import redirect
from core.utils import get_licenca_db_config
from ...models import Bensptr
from ...Web.Services.registrar_bens import BensptrService

class BensDeleteView(DeleteView):
    model = Bensptr
    template_name = 'Bens/bens_confirm_delete.html'

    def get_object(self, queryset=None):
        empresa = self.kwargs.get('bens_empr')
        filial = self.kwargs.get('bens_fili')
        codigo = self.kwargs.get('bens_codi')
        
        banco = get_licenca_db_config(self.request) or 'default'
        
        return Bensptr.objects.using(banco).get(
            bens_empr=empresa,
            bens_fili=filial,
            bens_codi=codigo
        )

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        banco = get_licenca_db_config(self.request) or 'default'
        
        BensptrService.delete_bem(self.object, using=banco)
        
        slug = self.kwargs.get('slug')
        return redirect('bens_web:bens_list', slug=slug)
