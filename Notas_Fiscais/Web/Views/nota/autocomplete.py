from django.http import JsonResponse
from django.db.models import Q

from core.utils import get_licenca_db_config
from Entidades.models import Entidades
from Produtos.models import Produtos, Tabelaprecos
from CFOP.models import CFOP    


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

    qs = CFOP.objects.using(banco).filter(cfop_empr=empresa)
    if q:
        qs = qs.filter(Q(cfop_codi__icontains=q) | Q(cfop_desc__iregex=q))

    qs = qs.only(
        "cfop_codi",
        "cfop_desc",
        "cfop_exig_icms",
        "cfop_exig_ipi",
        "cfop_exig_pis_cofins",
        "cfop_exig_cbs",
        "cfop_exig_ibs",
        "cfop_gera_st",
        "cfop_gera_difal",
    ).order_by("cfop_codi")[:20]

    data = [
        {
            "value": str(x.cfop_codi),
            "label": f"{x.cfop_codi} • {x.cfop_desc}",
            "cst_icms": ("000" if getattr(x, "cfop_exig_icms", False) else None),
            "cst_pis": ("01" if getattr(x, "cfop_exig_pis_cofins", False) else None),
            "cst_cofins": ("01" if getattr(x, "cfop_exig_pis_cofins", False) else None),
            "flags": {
                "exig_icms": getattr(x, "cfop_exig_icms", False),
                "exig_ipi": getattr(x, "cfop_exig_ipi", False),
                "exig_pis_cofins": getattr(x, "cfop_exig_pis_cofins", False),
                "exig_cbs": getattr(x, "cfop_exig_cbs", False),
                "exig_ibs": getattr(x, "cfop_exig_ibs", False),
                "gera_st": getattr(x, "cfop_gera_st", False),
                "gera_difal": getattr(x, "cfop_gera_difal", False),
            },
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
