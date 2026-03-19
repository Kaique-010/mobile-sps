from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View

from core.utils import get_licenca_db_config

from Lancamentos_Bancarios.services import deletar_entrada, deletar_saida


class LancamentoEntradaDeleteView(View):
    def post(self, request, slug=None, laba_ctrl=None):
        banco = get_licenca_db_config(request) or "default"
        try:
            deletar_entrada(banco=banco, laba_ctrl=int(laba_ctrl))
            messages.success(request, "Lançamento de entrada excluído com sucesso.")
        except Exception as e:
            messages.error(request, str(e))
        return redirect(reverse_lazy("lancamentos_bancarios_web:lancamentos_list", kwargs={"slug": slug}))


class LancamentoSaidaDeleteView(View):
    def post(self, request, slug=None, laba_ctrl=None):
        banco = get_licenca_db_config(request) or "default"
        try:
            deletar_saida(banco=banco, laba_ctrl=int(laba_ctrl))
            messages.success(request, "Lançamento de saída excluído com sucesso.")
        except Exception as e:
            messages.error(request, str(e))
        return redirect(reverse_lazy("lancamentos_bancarios_web:lancamentos_list", kwargs={"slug": slug}))

