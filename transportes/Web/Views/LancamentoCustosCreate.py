from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView

from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.forms.lancamento_custos import LancamentoCustosForm
from transportes.models import Custos
from transportes.services.servico_de_lancamento_custos import LancamentoCustosService


class LancamentoCustosCreateView(CreateView):
    model = Custos
    form_class = LancamentoCustosForm
    template_name = "transportes/lancamento_custos_form.html"

    def _get_banco(self):
        slug = self.kwargs.get("slug")
        return get_db_from_slug(slug) if slug else get_licenca_db_config(self.request)

    def get_success_url(self):
        return reverse("transportes:lancamento_custos_lista", kwargs={"slug": self.kwargs["slug"]})

    def form_valid(self, form):
        banco = self._get_banco()
        empresa_id = self.request.session.get("empresa_id")
        filial_id = self.request.session.get("filial_id") or 1
        usuario_id = self.request.session.get("usua_codi")

        if not empresa_id:
            messages.error(self.request, "Empresa não identificada na sessão.")
            return self.form_invalid(form)

        data = form.cleaned_data.copy()
        data["lacu_empr"] = int(empresa_id)
        data["lacu_fili"] = int(filial_id)

        try:
            self.object = LancamentoCustosService.create_custo(
                data=data,
                user_id=usuario_id,
                using=banco,
            )
        except ValueError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        messages.success(self.request, f"Lançamento de custo {self.object.lacu_ctrl} criado com sucesso!")
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Novo Lançamento de Custo"
        context["acao"] = "Criar"
        return context
