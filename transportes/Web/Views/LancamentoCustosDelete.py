from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DeleteView

from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.models import Custos
from transportes.services.servico_de_lancamento_custos import LancamentoCustosService


class LancamentoCustosDeleteView(DeleteView):
    model = Custos
    template_name = "transportes/lancamento_custos_delete.html"

    def _get_banco(self):
        slug = self.kwargs.get("slug")
        return get_db_from_slug(slug) if slug else get_licenca_db_config(self.request)

    def get_success_url(self):
        return reverse("transportes:lancamento_custos_lista", kwargs={"slug": self.kwargs["slug"]})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["slug"] = self.kwargs.get("slug")
        return context

    def get_object(self, queryset=None):
        banco = self._get_banco()
        empresa_id = self.request.session.get("empresa_id")
        filial_id = self.request.session.get("filial_id") or 1
        lacu_ctrl = self.kwargs.get("lacu_ctrl")
        return get_object_or_404(
            Custos.objects.using(banco),
            lacu_empr=empresa_id,
            lacu_fili=filial_id,
            lacu_ctrl=lacu_ctrl,
        )

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        banco = self._get_banco()
        usuario_id = request.session.get("usua_codi")
        try:
            LancamentoCustosService.delete_custo(
                custo=self.object,
                user_id=usuario_id,
                using=banco,
            )
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect(self.get_success_url())
        messages.success(request, "Lançamento de custo excluído com sucesso!")
        return redirect(self.get_success_url())
