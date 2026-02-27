from django.views.generic import DeleteView
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from core.utils import get_licenca_db_config
from transportes.models import Veiculos

class VeiculosDeleteView(DeleteView):
    model = Veiculos
    template_name = 'transportes/veiculos_delete.html'

    def get_success_url(self):
        return reverse('transportes:veiculos_lista', kwargs={'slug': self.kwargs['slug']})

    def get_object(self, queryset=None):
        banco = get_licenca_db_config(self.request)
        empresa_id = self.request.session.get('empresa_id')
        tran = self.kwargs.get('tran')
        sequ = self.kwargs.get('sequ')
        
        return get_object_or_404(
            Veiculos.objects.using(banco), 
            veic_empr=empresa_id, 
            veic_tran=tran, 
            veic_sequ=sequ
        )

    def delete(self, request, *args, **kwargs):
        banco = get_licenca_db_config(self.request)
        self.object = self.get_object()
        self.object.delete(using=banco)
        messages.success(request, 'Veículo excluído com sucesso!')
        return redirect(self.get_success_url())
