from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DeleteView

from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.models import Abastecusto
from transportes.services.servico_de_abastecimento import AbastecimentoService


class AbastecimentosDeleteView(DeleteView):
    model = Abastecusto
    template_name = "transportes/abastecimentos_delete.html"

    def _get_banco(self):
        slug = self.kwargs.get("slug")
        return get_db_from_slug(slug) if slug else get_licenca_db_config(self.request)

    def get_success_url(self):
        return reverse("transportes:abastecimentos_lista", kwargs={"slug": self.kwargs["slug"]})

    def get_object(self, queryset=None):
        banco = self._get_banco()
        empresa_id = self.request.session.get("empresa_id")
        filial_id = self.request.session.get("filial_id") or 1
        abas_ctrl = self.kwargs.get("abas_ctrl")
        return get_object_or_404(
            Abastecusto.objects.using(banco),
            abas_empr=empresa_id,
            abas_fili=filial_id,
            abas_ctrl=abas_ctrl,
        )

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        banco = self._get_banco()
        usuario_id = request.session.get("usua_codi")
        try:
            AbastecimentoService.delete_abastecimento(
                abastecimento=self.object,
                user_id=usuario_id,
                using=banco,
            )
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect(self.get_success_url())
        messages.success(request, "Abastecimento excluído com sucesso!")
        return redirect(self.get_success_url())
