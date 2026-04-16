from django.views.generic import UpdateView
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from core.utils import get_licenca_db_config
from transportes.models import Veiculos
from transportes.forms.VeiculosForm import VeiculosForm
from transportes.services.VeiculosService import VeiculosService
from Entidades.models import Entidades
from Produtos.models import Marca
from CentrodeCustos.models import Centrodecustos

class VeiculosUpdateView(UpdateView):
    model = Veiculos
    form_class = VeiculosForm
    template_name = 'transportes/veiculos_form.html'

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

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request)
        
        # Recupera os dados do form mas não salva ainda
        self.object = form.save(commit=False)

        # Chaves originais para garantir que estamos atualizando o registro correto
        empresa_id = self.request.session.get('empresa_id')
        tran_orig = self.kwargs.get('tran')
        sequ_orig = self.kwargs.get('sequ')

        # Campos da chave primária composta que não devem ser alterados no update
        pk_fields = ['veic_empr', 'veic_tran', 'veic_sequ']
        
        # Prepara o dicionário de dados para o update
        update_data = {}
        for field_name, value in form.cleaned_data.items():
            if field_name not in pk_fields:
                update_data[field_name] = value

        # Realiza o update filtrando pela chave composta completa
        # Isso evita o problema do Django tentar atualizar todos os registros com veic_empr=X
        Veiculos.objects.using(banco).filter(
            veic_empr=empresa_id,
            veic_tran=tran_orig,
            veic_sequ=sequ_orig
        ).update(**update_data)

        messages.success(self.request, 'Veículo atualizado com sucesso!')
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request)
        empresa_id = self.request.session.get('empresa_id')

        # Transportadora
        if self.object.veic_tran:
            try:
                tran = Entidades.objects.using(banco).filter(enti_empr=empresa_id, enti_clie=self.object.veic_tran).first()
                if tran:
                    context['transportadora_nome'] = f"{tran.enti_clie} - {tran.enti_nome}"
            except Exception:
                pass

        # Marca
        if self.object.veic_marc:
            try:
                marc = Marca.objects.using(banco).filter(codigo=self.object.veic_marc).first()
                if marc:
                    context['marca_nome'] = f"{marc.codigo} - {marc.nome}"
            except Exception:
                pass

        # Centro de Custos
        if self.object.veic_cecu:
            try:
                cecu = Centrodecustos.objects.using(banco).filter(cecu_empr=empresa_id, cecu_redu=self.object.veic_cecu).first()
                if cecu:
                    context['cecu_nome'] = f"{cecu.cecu_redu} - {cecu.cecu_nome}"
            except Exception:
                pass

        # Motorista
        if self.object.veic_moto:
            try:
                moto = Entidades.objects.using(banco).filter(enti_empr=empresa_id, enti_clie=self.object.veic_moto).first()
                if moto:
                    context['motorista_nome'] = f"{moto.enti_clie} - {moto.enti_nome}"
            except Exception:
                pass

        return context
