from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from core.utils import get_licenca_db_config
from comissoes.models import RegraComissao
from comissoes.services import CadastroComissaoService
from comissoes.Web.forms import RegraComissaoForm
from Entidades.models import Entidades


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
    banco = get_licenca_db_config(request) or "default"
    empresa_id = request.session.get("empresa_id")
    bene_ids = [int(x) for x in regras.values_list("regc_bene", flat=True) if x is not None]
    bene_map = {}
    if bene_ids:
        bene_map = {
            int(e.enti_clie): str(e.enti_nome or "")
            for e in Entidades.objects.using(banco)
            .filter(enti_empr=int(empresa_id), enti_clie__in=bene_ids)
            .only("enti_clie", "enti_nome")
        }
    for r in regras:
        nome = bene_map.get(int(r.regc_bene)) if getattr(r, "regc_bene", None) is not None else None
        if nome:
            r.beneficiario_nome = nome
            r.beneficiario_display = f"{r.regc_bene} - {nome}"
        else:
            r.beneficiario_nome = ""
            r.beneficiario_display = str(r.regc_bene)
    return render(request, "comissoes/regras_list.html", {"regras": regras, "slug": slug})


@require_http_methods(["GET", "POST"])
def criar(request, slug=None):
    if request.method == "POST":
        form = RegraComissaoForm(request.POST, request=request)
        if form.is_valid():
            service = _service(request)
            data = form.cleaned_data
            try:
                service.salvar_regra(
                    beneficiario_id=data["regc_bene"],
                    percentual=data["regc_perc"],
                    ativo=data.get("regc_ativ", True),
                    data_ini=data.get("regc_data_ini"),
                    data_fim=data.get("regc_data_fim"),
                )
                messages.success(request, "Salvo com sucesso.")
                return redirect("comissoes_web:regras_list", slug=slug)
            except Exception as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Verifique os campos e tente novamente.")
    else:
        form = RegraComissaoForm(request=request)
    return render(request, "comissoes/regras_form.html", {"form": form, "slug": slug})


@require_http_methods(["GET", "POST"])
def editar(request, slug=None, regra_id=None):
    banco = get_licenca_db_config(request) or "default"
    empresa_id = request.session.get("empresa_id")
    filial_id = request.session.get("filial_id")
    if not empresa_id or not filial_id:
        messages.error(request, "Selecione empresa e filial para continuar.")
        return redirect("comissoes_web:regras_list", slug=slug)

    regra = get_object_or_404(
        RegraComissao.objects.using(banco),
        regc_id=int(regra_id),
        regc_empr=int(empresa_id),
        regc_fili=int(filial_id),
    )

    if request.method == "POST":
        form = RegraComissaoForm(request.POST, instance=regra, request=request)
        if form.is_valid():
            service = CadastroComissaoService(db_alias=banco, empresa_id=int(empresa_id), filial_id=int(filial_id))
            data = form.cleaned_data
            try:
                service.atualizar_regra(
                    regra_id=regra.regc_id,
                    beneficiario_id=data["regc_bene"],
                    percentual=data["regc_perc"],
                    ativo=data.get("regc_ativ", True),
                    data_ini=data.get("regc_data_ini"),
                    data_fim=data.get("regc_data_fim"),
                )
                messages.success(request, "Editado com sucesso.")
                return redirect("comissoes_web:regras_list", slug=slug)
            except Exception as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Verifique os campos e tente novamente.")
    else:
        form = RegraComissaoForm(instance=regra, request=request)

    return render(
        request,
        "comissoes/regras_form.html",
        {"form": form, "slug": slug, "modo_edicao": True, "regra": regra},
    )
