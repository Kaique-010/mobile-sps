from django.shortcuts import redirect, render, get_object_or_404
from django.views.generic import View

from core.mixin import DBAndSlugMixin
from nfse.models import Nfse
from nfse.Web.forms import NfseForm
from nfse.services.context import NfseContext
from nfse.services.cancelamento_service import CancelamentoNfseService




class NfseDeleteView(DBAndSlugMixin, View):
    template_name = 'nfse/confirm_delete.html'

    def get_obj(self, pk):
        return get_object_or_404(
            Nfse.objects.using(self.request.db_alias),
            nfse_id=pk,
            nfse_empr=self.empresa_id,
            nfse_fili=self.filial_id,
        )

    def get(self, request, pk, *args, **kwargs):
        nota = self.get_obj(pk)
        return render(request, self.template_name, {
            'nota': nota,
            'slug': self.slug,
        })

    def post(self, request, pk, *args, **kwargs):
        nota = self.get_obj(pk)
        nota.delete(using=request.db_alias)
        messages.success(request, 'Registro removido com sucesso.')
        return redirect('nfse_web:listar', slug=self.slug)
