from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.views import View

from core.utils import get_licenca_db_config
from sped.Services.gerador import GeradorSpedService
from sped.Web.forms import GerarSpedForm


def _to_int(v):
    try:
        return int(v)
    except Exception:
        return None


class SpedGerarView(View):
    template_name = "sped/gerar.html"

    def dispatch(self, request, *args, **kwargs):
        self.db_alias = get_licenca_db_config(request)
        self.slug = kwargs.get("slug")
        self.empresa_id = request.session.get("empresa_id")
        self.filial_id = request.session.get("filial_id")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = GerarSpedForm()
        return render(request, self.template_name, {"form": form, "slug": self.slug})

    def post(self, request, *args, **kwargs):
        form = GerarSpedForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "slug": self.slug})

        if not self.db_alias:
            messages.error(request, "Banco de dados não encontrado.")
            return render(request, self.template_name, {"form": form, "slug": self.slug})

        if not self.empresa_id or not self.filial_id:
            messages.error(request, "Empresa e filial são obrigatórias.")
            return render(request, self.template_name, {"form": form, "slug": self.slug})

        texto = GeradorSpedService(
            db_alias=self.db_alias,
            empresa_id=self.empresa_id,
            filial_id=self.filial_id,
            data_inicio=form.cleaned_data["data_inicio"],
            data_fim=form.cleaned_data["data_fim"],
            cod_receita=form.cleaned_data.get("cod_receita"),
            data_vencimento=form.cleaned_data.get("data_vencimento"),
        ).gerar()

        nome = "SPED_{empresa}_{filial}_{ini}_{fim}.txt".format(
            empresa=self.empresa_id,
            filial=self.filial_id,
            ini=form.cleaned_data["data_inicio"].strftime("%Y%m%d"),
            fim=form.cleaned_data["data_fim"].strftime("%Y%m%d"),
        )
        resp = HttpResponse(texto, content_type="text/plain; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="{0}"'.format(nome)
        return resp
