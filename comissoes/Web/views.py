from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from core.utils import get_licenca_db_config
from comissoes.models import RegraComissao
from comissoes.services import CadastroComissaoService
from .forms import RegraComissaoForm


def painel_view(request, slug=None):
    return render(request, "comissoes/base.html", {"slug": slug})


def _service(request):
    banco = get_licenca_db_config(request) or "default"
    empresa_id = request.session.get("empresa_id")
    filial_id = request.session.get("filial_id")
    if not empresa_id or not filial_id:
        raise ValueError("Selecione empresa e filial para continuar.")
    return CadastroComissaoService(db_alias=banco, empresa_id=int(empresa_id), filial_id=int(filial_id))


def lista(request, slug=None):
    service = _service(request)
    regras = service.listar_regras()
    return render(request, "comissoes/regras_list.html", {"regras": regras, "slug": slug})


@require_http_methods(["GET", "POST"])
def criar(request, slug=None):
    if request.method == "POST":
        form = RegraComissaoForm(request.POST, request=request)
        if form.is_valid():
            service = _service(request)
            data = form.cleaned_data
            service.salvar_regra(
                beneficiario_id=data["regc_bene"],
                percentual=data["regc_perc"],
                ativo=data.get("regc_ativ", True),
                data_ini=data.get("regc_data_ini"),
                data_fim=data.get("regc_data_fim"),
            )
            messages.success(request, "Regra salva com sucesso.")
            return redirect("comissoes_web:regras_list", slug=slug)
    else:
        form = RegraComissaoForm(request=request)
    return render(request, "comissoes/regras_form.html", {"form": form, "slug": slug})
