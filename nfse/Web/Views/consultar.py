from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.generic import View

from core.mixin import DBAndSlugMixin
from nfse.services.consulta_service import ConsultaNfseService
from nfse.services.context import NfseContext


class NfseConsultarView(DBAndSlugMixin, View):
    def post(self, request, pk, *args, **kwargs):
        context = NfseContext.from_request(request, self.slug)

        try:
            ConsultaNfseService.consultar(context, pk)
            messages.success(request, 'Consulta realizada com sucesso.')
        except Exception as exc:
            messages.error(request, f'Erro ao consultar NFS-e: {exc}')

        return redirect('nfse_web:detalhe', slug=self.slug, pk=pk)