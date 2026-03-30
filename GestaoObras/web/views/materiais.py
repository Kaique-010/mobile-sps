from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.forms.utils import ErrorList
from core.utils import get_licenca_db_config
from GestaoObras.web.forms import ObraMaterialMovimentoForm, ObraMaterialMovimentoCabecalhoForm, ObraMaterialMovimentoItemFormSet
from GestaoObras.models import Obra, ObraEtapa, ObraMaterialMovimento
from GestaoObras.services.obras_service import ObrasService


def listar_materiais(request, slug, obra_id: int):
    banco = get_licenca_db_config(request)
    obra = get_object_or_404(Obra.objects.using(banco), pk=obra_id)
    qs = ObraMaterialMovimento.objects.using(banco).filter(movm_obra_id=obra.id).order_by("-movm_data", "-movm_codi")
    etapa_id = request.GET.get("etapa_id")
    if etapa_id:
        qs = qs.filter(movm_etap_id=etapa_id)
    etapas = ObraEtapa.objects.using(banco).filter(etap_obra_id=obra.id).order_by("etap_orde", "id")
    return render(
        request,
        "obras/materiais_listar.html",
        {"slug": slug, "obra": obra, "movimentos": qs, "etapas": etapas, "etapa_id": etapa_id},
    )


def criar_movimento_material(request, slug, obra_id: int):
    banco = get_licenca_db_config(request)
    obra = get_object_or_404(Obra.objects.using(banco), pk=obra_id)
    initial = {
        "movm_empr": obra.obra_empr,
        "movm_fili": obra.obra_fili,
        "movm_obra": obra.id,
        "movm_tipo": request.GET.get("tipo") or "SA",
        "movm_codi": ObrasService.proximo_codigo_movimento_material(banco, obra.obra_empr, obra.obra_fili),
    }
    if request.method == "POST":
        cab_form = ObraMaterialMovimentoCabecalhoForm(request.POST, banco=banco, initial=initial)
        formset = ObraMaterialMovimentoItemFormSet(request.POST, prefix="itens")
        if cab_form.is_valid() and formset.is_valid():
            cab = cab_form.cleaned_data
            if cab.get("movm_etap") and cab.get("movm_etap").etap_obra_id != obra.id:
                cab["movm_etap"] = None
            itens = []
            for f in formset.forms:
                cd = f.cleaned_data
                prod = (cd.get("movm_prod") or "").strip()
                if not prod:
                    continue
                itens.append(cd)
            if not itens:
                formset._non_form_errors = ErrorList(["Informe ao menos um item de produto."])
            else:
                try:
                    opcoes_fin = {
                        "tipo": (request.POST.get("fin_tipo") or "").strip() or ("DE" if (cab.get("movm_tipo") or "SA") == "SA" else "RE"),
                        "parcelas": request.POST.get("fin_parcelas") or "1",
                        "primeiro_vencimento": request.POST.get("fin_primeiro_venc") or cab.get("movm_data"),
                        "intervalo_dias": request.POST.get("fin_intervalo") or "30",
                    }
                    ObrasService.registrar_movimentos_materiais_lote(
                        banco=banco,
                        obra=obra,
                        cabecalho={
                            "movm_codi": cab.get("movm_codi"),
                            "movm_data": cab.get("movm_data"),
                            "movm_tipo": cab.get("movm_tipo"),
                            "movm_etap_id": cab.get("movm_etap").id if cab.get("movm_etap") else None,
                            "movm_docu": cab.get("movm_docu"),
                            "movm_obse": cab.get("movm_obse"),
                        },
                        itens=itens,
                        gerar_financeiro=bool(cab.get("gerar_financeiro")),
                        opcoes_financeiro=opcoes_fin if cab.get("gerar_financeiro") else None,
                    )
                except ValueError as e:
                    cab_form.add_error("movm_codi", str(e))
                else:
                    ObrasService.consolidar_custo_obra(obra=obra, banco=banco)
                    return redirect("gestaoobras:obras_materiais_list", slug=slug, obra_id=obra.id)
    else:
        cab_form = ObraMaterialMovimentoCabecalhoForm(banco=banco, initial=initial)
        formset = ObraMaterialMovimentoItemFormSet(prefix="itens")

    return render(
        request,
        "obras/materiais_criar.html",
        {"slug": slug, "obra": obra, "cab_form": cab_form, "itens_formset": formset},
    )


def editar_movimento_material(request, slug, obra_id: int, movimento_id: int):
    banco = get_licenca_db_config(request)
    obra = get_object_or_404(Obra.objects.using(banco), pk=obra_id)
    movimento = get_object_or_404(ObraMaterialMovimento.objects.using(banco), pk=movimento_id, movm_obra_id=obra.id)
    initial = {
        "movm_empr": obra.obra_empr,
        "movm_fili": obra.obra_fili,
        "movm_obra": obra.id,
    }
    if request.method == "POST":
        form = ObraMaterialMovimentoForm(request.POST, banco=banco, initial=initial, instance=movimento)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.movm_empr = obra.obra_empr
            obj.movm_fili = obra.obra_fili
            obj.movm_obra_id = obra.id
            if obj.movm_etap_id:
                exists = ObraEtapa.objects.using(banco).filter(pk=obj.movm_etap_id, etap_obra_id=obra.id).exists()
                if not exists:
                    obj.movm_etap_id = None
            obj.save(using=banco)
            if form.cleaned_data.get("gerar_financeiro"):
                ObrasService.gerar_financeiro_do_movimento_material(banco=banco, obra=obra, movimento=obj)
            ObrasService.consolidar_custo_obra(obra=obra, banco=banco)
            return redirect("gestaoobras:obras_detail", slug=slug, obra_id=obra.id)
    else:
        form = ObraMaterialMovimentoForm(banco=banco, initial=initial, instance=movimento)
    return render(request, "obras/materiais_criar.html", {"slug": slug, "obra": obra, "form": form})


def autocomplete_produtos(request, slug=None):
    banco = get_licenca_db_config(request) or "default"
    empresa_id = request.session.get("empresa_id", 1)
    term = (request.GET.get("term") or request.GET.get("q") or "").strip()

    from Produtos.models import Produtos

    qs = Produtos.objects.using(banco).filter(prod_empr=str(empresa_id)).select_related("prod_unme")
    if term:
        if term.isdigit():
            qs = qs.filter(prod_codi__icontains=term)
        else:
            qs = qs.filter(prod_nome__icontains=term)
    qs = qs.order_by("prod_nome")[:20]

    data = []
    for obj in qs:
        unid_codi = getattr(obj, "prod_unme_id", "") or ""
        unid_desc = ""
        try:
            unid_desc = getattr(getattr(obj, "prod_unme", None), "unid_desc", "") or str(getattr(obj, "prod_unme", "") or "")
        except Exception:
            unid_desc = ""
        data.append(
            {
                "id": str(obj.prod_codi),
                "text": f"{obj.prod_codi} - {obj.prod_nome}",
                "prod_nome": obj.prod_nome,
                "unid_codi": str(unid_codi),
                "unid_desc": unid_desc,
                "prod_ncm": getattr(obj, "prod_ncm", None),
                "prod_gtin": getattr(obj, "prod_gtin", None),
                "prod_coba": getattr(obj, "prod_coba", None),
                "prod_loca": getattr(obj, "prod_loca", None),
                "prod_codi_serv": getattr(obj, "prod_codi_serv", None),
                "prod_desc_serv": getattr(obj, "prod_desc_serv", None),
                "prod_e_serv": bool(getattr(obj, "prod_e_serv", False)),
            }
        )

    return JsonResponse({"results": data})
