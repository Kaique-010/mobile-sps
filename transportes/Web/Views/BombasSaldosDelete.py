from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DeleteView

from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.models import BombasSaldos
from transportes.services.bombas_saldos import BombasSaldosService


class BombasSaldosDeleteView(DeleteView):
    model = BombasSaldos
    template_name = "transportes/bombas_saldos_delete.html"

    def _get_banco(self):
        slug = self.kwargs.get("slug")
        return get_db_from_slug(slug) if slug else get_licenca_db_config(self.request)

    def get_success_url(self):
        return reverse("transportes:bombas_saldos_lista", kwargs={"slug": self.kwargs["slug"]})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["slug"] = self.kwargs.get("slug")
        return context

    def get_object(self, queryset=None):
        banco = self._get_banco()
        empresa_id = self.request.session.get("empresa_id")
        filial_id = self.request.session.get("filial_id") or 1
        bomb_id = self.kwargs.get("bomb_id")
        return get_object_or_404(
            BombasSaldos.objects.using(banco),
            bomb_id=bomb_id,
            bomb_empr=empresa_id,
            bomb_fili=filial_id,
        )

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        banco = self._get_banco()
        empresa_id = self.request.session.get("empresa_id")
        filial_id = self.request.session.get("filial_id") or 1

        try:
            saldo_atual, saldo_depois = BombasSaldosService.excluir_movimentacao(
                using=banco,
                empresa_id=int(empresa_id),
                filial_id=int(filial_id),
                bomb_id=int(self.object.bomb_id),
            )
        except Exception as exc:
            messages.error(request, str(exc))
            return redirect(self.get_success_url())

        messages.success(request, f"Movimentação excluída. Saldo: {saldo_atual} → {saldo_depois}")
        return redirect(self.get_success_url())

