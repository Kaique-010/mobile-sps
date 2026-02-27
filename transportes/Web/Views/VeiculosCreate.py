from django.views.generic import CreateView
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib import messages
from core.utils import get_licenca_db_config
from transportes.models import Veiculos
from transportes.Forms.VeiculosForm import VeiculosForm
from transportes.Services.VeiculosService import VeiculosService

class VeiculosCreateView(CreateView):
    model = Veiculos
    form_class = VeiculosForm
    template_name = 'transportes/veiculos_form.html'

    def get_success_url(self):
        return reverse('transportes:veiculos_lista', kwargs={'slug': self.kwargs['slug']})

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request)
        empresa_id = self.request.session.get('empresa_id')
        
        if not empresa_id:
            messages.error(self.request, "Empresa não identificada na sessão. Por favor, faça login novamente.")
            return self.form_invalid(form)

        transportadora_id = form.cleaned_data['veic_tran']
        
        sequencial = VeiculosService.gerar_sequencial(empresa_id, transportadora_id, using=banco)
        
        # Salva o objeto manualmente para garantir o banco correto e force_insert
        self.object = form.save(commit=False)
        
        # Atribui os campos da chave composta manualmente APÓS save(commit=False)
        self.object.veic_empr = empresa_id
        self.object.veic_sequ = sequencial
        
        self.object.save(using=banco, force_insert=True)
        
        messages.success(self.request, f'Veículo {sequencial} criado com sucesso!')
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Novo Veículo'
        context['acao'] = 'Criar'
        return context
