from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView

from core.utils import get_licenca_db_config

from Lancamentos_Bancarios.forms import LancamentoBancarioForm
from Lancamentos_Bancarios.services import criar_entrada, criar_saida


class LancamentoEntradaCreateView(CreateView):
    template_name = "Lancamentos_Bancarios/Lancamento_form.html"
    form_class = LancamentoBancarioForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["db_alias"] = get_licenca_db_config(self.request) or "default"
        kwargs["empresa_id"] = self.request.session.get("empresa_id")
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        empresa_id = self.request.session.get("empresa_id")
        filial_id = self.request.session.get("filial_id")
        if empresa_id is not None:
            initial["laba_empr"] = empresa_id
        if filial_id is not None:
            initial["laba_fili"] = filial_id
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["slug"] = self.kwargs.get("slug")
        ctx["tipo_label"] = "Entrada"
        return ctx

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or "default"
        try:
            dados = {k: form.cleaned_data.get(k) for k in form._meta.fields}
            self.object = criar_entrada(banco=banco, dados=dados)
        except Exception as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        messages.success(self.request, "Lançamento de entrada criado com sucesso.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy("lancamentos_bancarios_web:lancamentos_list", kwargs={"slug": self.kwargs.get("slug")})


class LancamentoSaidaCreateView(CreateView):
    template_name = "Lancamentos_Bancarios/Lancamento_form.html"
    form_class = LancamentoBancarioForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["db_alias"] = get_licenca_db_config(self.request) or "default"
        kwargs["empresa_id"] = self.request.session.get("empresa_id")
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        empresa_id = self.request.session.get("empresa_id")
        filial_id = self.request.session.get("filial_id")
        if empresa_id is not None:
            initial["laba_empr"] = empresa_id
        if filial_id is not None:
            initial["laba_fili"] = filial_id
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["slug"] = self.kwargs.get("slug")
        ctx["tipo_label"] = "Saída"
        return ctx

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or "default"
        try:
            dados = {k: form.cleaned_data.get(k) for k in form._meta.fields}
            self.object = criar_saida(banco=banco, dados=dados)
        except Exception as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        messages.success(self.request, "Lançamento de saída criado com sucesso.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy("lancamentos_bancarios_web:lancamentos_list", kwargs={"slug": self.kwargs.get("slug")})
