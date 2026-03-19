from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from core.utils import get_licenca_db_config

from Lancamentos_Bancarios.forms import LancamentoBancarioForm
from Lancamentos_Bancarios.models import Lctobancario
from Lancamentos_Bancarios.services import atualizar_entrada, atualizar_saida


class LancamentoEntradaUpdateView(UpdateView):
    template_name = "Lancamentos_Bancarios/Lancamento_form.html"
    form_class = LancamentoBancarioForm
    model = Lctobancario
    pk_url_kwarg = "laba_ctrl"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["db_alias"] = get_licenca_db_config(self.request) or "default"
        kwargs["empresa_id"] = self.request.session.get("empresa_id")
        return kwargs

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or "default"
        return Lctobancario.objects.using(banco).filter(laba_dbcr="C")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["slug"] = self.kwargs.get("slug")
        ctx["tipo_label"] = "Entrada"
        return ctx

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or "default"
        try:
            self.object = atualizar_entrada(banco=banco, laba_ctrl=int(self.kwargs["laba_ctrl"]), dados=form.cleaned_data)
        except Exception as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        messages.success(self.request, "Lançamento de entrada atualizado com sucesso.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy("lancamentos_bancarios_web:lancamentos_list", kwargs={"slug": self.kwargs.get("slug")})


class LancamentoSaidaUpdateView(UpdateView):
    template_name = "Lancamentos_Bancarios/Lancamento_form.html"
    form_class = LancamentoBancarioForm
    model = Lctobancario
    pk_url_kwarg = "laba_ctrl"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["db_alias"] = get_licenca_db_config(self.request) or "default"
        kwargs["empresa_id"] = self.request.session.get("empresa_id")
        return kwargs

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or "default"
        return Lctobancario.objects.using(banco).filter(laba_dbcr="D")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["slug"] = self.kwargs.get("slug")
        ctx["tipo_label"] = "Saída"
        return ctx

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or "default"
        try:
            self.object = atualizar_saida(banco=banco, laba_ctrl=int(self.kwargs["laba_ctrl"]), dados=form.cleaned_data)
        except Exception as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        messages.success(self.request, "Lançamento de saída atualizado com sucesso.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy("lancamentos_bancarios_web:lancamentos_list", kwargs={"slug": self.kwargs.get("slug")})
