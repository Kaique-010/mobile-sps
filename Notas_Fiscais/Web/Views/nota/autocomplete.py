from django.http import JsonResponse
from django.db.models import Q

from core.utils import get_licenca_db_config
from Entidades.models import Entidades
from Produtos.models import Produtos, Tabelaprecos
from CFOP.models import Cfop


def entidades_autocomplete(request, slug=None):
    banco = get_licenca_db_config(request) or "default"
    empresa = request.session.get("empresa_id")
    q = (request.GET.get("q") or "").strip()

    qs = Entidades.objects.using(banco).filter(enti_empr=empresa)
    if q:
        qs = qs.filter(
            Q(enti_nome__iregex=q) | Q(enti_cnpj__icontains=q) | Q(enti_cpf__icontains=q)
        )

    qs = qs.only("enti_clie", "enti_nome", "enti_cnpj", "enti_cpf").order_by("enti_nome")[:20]
    data = [
        {
            "value": e.enti_clie,
            "label": f"{e.enti_nome} • {(e.enti_cnpj or e.enti_cpf or '')}",
            "enti_clie": e.enti_clie,
            "enti_nome": e.enti_nome,
            "enti_cnpj": e.enti_cnpj,
            "enti_cpf": e.enti_cpf,
        }
        for e in qs
    ]
    return JsonResponse(data, safe=False)


def produtos_autocomplete(request, slug=None):
    banco = get_licenca_db_config(request) or "default"
    empresa = request.session.get("empresa_id")
    q = (request.GET.get("q") or "").strip()

    qs = Produtos.objects.using(banco).filter(prod_empr=empresa)
    if q:
        qs = qs.filter(
            Q(prod_nome__iregex=q) | Q(prod_codi__iexact=q) | Q(prod_codi_nume__iexact=q) | Q(prod_coba__iexact=q)
        )

    qs = qs.only("prod_codi", "prod_nome", "prod_coba").order_by("prod_nome")[:20]
    data = [
        {
            "value": p.prod_codi,
            "label": f"{p.prod_nome} • COD: {p.prod_codi}{(' • REF: ' + p.prod_coba) if p.prod_coba else ''}",
            "prod_desc": p.prod_nome,
            "prod_codi": p.prod_codi,
            "prod_refe": getattr(p, "prod_coba", None),
        }
        for p in qs
    ]
    return JsonResponse(data, safe=False)


def produto_detalhe(request, slug=None, codigo=None):
    banco = get_licenca_db_config(request) or "default"
    empresa = request.session.get("empresa_id")
    p = Produtos.objects.using(banco).filter(prod_empr=empresa, prod_codi=codigo).select_related("prod_unme").first()
    if not p:
        return JsonResponse({"detail": "Produto não encontrado"}, status=404)

    data = {
        "prod_codi": p.prod_codi,
        "prod_desc": p.prod_nome,
        "prod_unid": getattr(getattr(p, "prod_unme", None), "unid_codi", "UN"),
        "prod_ncm": getattr(p, "prod_ncm", ""),
    }
    preco = (
        Tabelaprecos.objects.using(banco)
        .filter(tabe_empr=empresa, tabe_prod=p.prod_codi)
        .values_list("tabe_avis", flat=True)
        .first()
    )
    if preco:
        data["prod_preco_vista"] = float(preco)
    return JsonResponse(data)


def cfop_autocomplete(request, slug=None):
    banco = get_licenca_db_config(request) or "default"
    empresa = request.session.get("empresa_id")
    q = (request.GET.get("q") or "").strip()

    qs = Cfop.objects.using(banco).filter(cfop_empr=empresa)
    if q:
        qs = qs.filter(Q(cfop_cfop__icontains=q) | Q(cfop_desc__iregex=q))

    qs = qs.only(
        "cfop_cfop",
        "cfop_desc",
        "cfop_trib_cst_icms",
        "cfop_trib_cst_pis",
        "cfop_trib_cst_cofins",
        "cfop_trib_aliq_ipi",
        "cfop_trib_perc_pis",
        "cfop_trib_perc_cofins",
    ).order_by("cfop_cfop")[:20]

    data = [
        {
            "value": str(x.cfop_cfop),
            "label": f"{x.cfop_cfop} • {x.cfop_desc}",
            "cst_icms": getattr(x, "cfop_trib_cst_icms", None),
            "cst_pis": getattr(x, "cfop_trib_cst_pis", None),
            "cst_cofins": getattr(x, "cfop_trib_cst_cofins", None),
            "ipi_aliquota": getattr(x, "cfop_trib_aliq_ipi", None),
            "pis_aliquota": getattr(x, "cfop_trib_perc_pis", None),
            "cofins_aliquota": getattr(x, "cfop_trib_perc_cofins", None),
        }
        for x in qs
    ]
    return JsonResponse(data, safe=False)


def transportadoras_autocomplete(request, slug=None):
    banco = get_licenca_db_config(request) or "default"
    empresa = request.session.get("empresa_id")
    q = (request.GET.get("q") or "").strip()

    qs = Entidades.objects.using(banco).filter(enti_empr=empresa)
    if q:
        qs = qs.filter(
            Q(enti_nome__iregex=q) | Q(enti_cnpj__icontains=q) | Q(enti_cpf__icontains=q)
        )

    qs = qs.only("enti_clie", "enti_nome", "enti_cnpj", "enti_cpf").order_by("enti_nome")[:20]
    data = [
        {
            "value": e.enti_clie,
            "label": f"{e.enti_nome} • {(e.enti_cnpj or e.enti_cpf or '')}",
            "enti_clie": e.enti_clie,
            "enti_nome": e.enti_nome,
            "enti_cnpj": e.enti_cnpj,
            "enti_cpf": e.enti_cpf,
        }
        for e in qs
    ]
    return JsonResponse(data, safe=False)