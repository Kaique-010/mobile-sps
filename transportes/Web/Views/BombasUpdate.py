from django.views.generic import UpdateView
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.models import Bombas
from transportes.forms.bombas import BombasForm
from Entidades.models import Entidades
from CentrodeCustos.models import Centrodecustos

class BombasUpdateView(UpdateView):
    model = Bombas
    form_class = BombasForm
    template_name = 'transportes/bombas_form.html'

    def get_success_url(self):
        return reverse('transportes:bombas_lista', kwargs={'slug': self.kwargs['slug']})

    def _get_banco(self):
        slug = self.kwargs.get('slug')
        return get_db_from_slug(slug) if slug else get_licenca_db_config(self.request)

    def get_object(self, queryset=None):
        banco = self._get_banco()
        empresa_id = self.request.session.get('empresa_id')
        bomba_codigo = self.kwargs.get('bomb_codi')
        
        return get_object_or_404(
            Bombas.objects.using(banco), 
            bomb_empr=empresa_id, 
            bomb_codi=bomba_codigo
        )

    def form_valid(self, form):
        banco = self._get_banco()
        
        # Recupera os dados do form mas não salva ainda
        self.object = form.save(commit=False)

        # Chaves originais para garantir que estamos atualizando o registro correto
        empresa_id = self.request.session.get('empresa_id')
        bomba_codigo = self.kwargs.get('bomb_codi')

        # Campos da chave primária composta que não devem ser alterados no update
        pk_fields = ['bomb_empr', 'bomb_codi']
        
        # Prepara o dicionário de dados para o update
        update_data = {}
        for field_name, value in form.cleaned_data.items():
            if field_name not in pk_fields:
                update_data[field_name] = value

        # Realiza o update filtrando pela chave composta completa
        # Isso evita o problema do Django tentar atualizar todos os registros com veic_empr=X
        Bombas.objects.using(banco).filter(
            bomb_empr=empresa_id,
            bomb_codi=bomba_codigo
        ).update(**update_data)

        messages.success(self.request, 'Bomba atualizada com sucesso!')
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = self._get_banco()
        empresa_id = self.request.session.get('empresa_id')

        # Centro de Custos
        if self.object.bomb_cecu:
            try:
                cecu = Centrodecustos.objects.using(banco).filter(cecu_empr=empresa_id, cecu_redu=self.object.bomb_cecu).first()
                if cecu:
                    context['cecu_nome'] = f"{cecu.cecu_redu} - {cecu.cecu_nome}"
            except Exception:
                pass

        # Entidade fornecedora
        if self.object.bomb_forn:
            try:
                enti = Entidades.objects.using(banco).filter(enti_empr=empresa_id, enti_clie=self.object.bomb_forn).first()
                if enti:
                    context['fornecedor_nome'] = f"{enti.enti_clie} - {enti.enti_nome}"
            except Exception:
                pass

        return context
