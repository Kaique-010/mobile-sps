from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import UpdateView

from Entidades.models import Entidades
from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.forms.TranspMotoForm import TranspMotoForm
from transportes.services.transp_moto_sync_service import TranspMotoSyncService


class TranspMotoUpdateView(UpdateView):
    model = Entidades
    form_class = TranspMotoForm
    template_name = 'transportes/transp_moto_form.html'
    context_object_name = 'entidade'

    def _get_banco(self):
        slug = self.kwargs.get('slug')
        return get_db_from_slug(slug) if slug else get_licenca_db_config(self.request)

    def get_object(self, queryset=None):
        banco = self._get_banco()
        empresa_id = self.request.session.get('empresa_id')
        enti_clie = self.kwargs.get('enti_clie')
        return get_object_or_404(
            Entidades.objects.using(banco),
            enti_empr=empresa_id,
            enti_clie=enti_clie,
            enti_tien__in=['T', 'M'],
        )

    def form_valid(self, form):
        banco = self._get_banco()
        empresa_id = self.request.session.get('empresa_id')
        filial_id = self.request.session.get('filial_id') or 1

        self.object = form.save(commit=False)
        self.object.save(using=banco)

        if self.object.enti_tien == 'M':
            TranspMotoSyncService.sync_entidade_para_motorista(
                banco=banco,
                empresa_id=empresa_id,
                filial_id=filial_id,
                entidade_id=self.object.enti_clie,
            )

        messages.success(self.request, 'Cadastro atualizado com sucesso.')
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('transportes:transportadoras_motoristas_lista', kwargs={'slug': self.kwargs['slug']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Transportadora/Motorista'
        context['slug'] = self.kwargs.get('slug')
        return context
