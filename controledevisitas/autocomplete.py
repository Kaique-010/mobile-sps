from django.http import JsonResponse
from django.db.models import Q

from core.utils import get_licenca_db_config
from Entidades.models import Entidades
from Produtos.models import Produtos
from .models import Etapavisita


def _get_pagination(request):
    try:
        limit = int(request.GET.get("limit", 10))
    except Exception:
        limit = 10
    try:
        offset = int(request.GET.get("offset", 0))
    except Exception:
        offset = 0
    if limit < 1:
        limit = 10
    if limit > 50:
        limit = 50
    if offset < 0:
        offset = 0
    return limit, offset


def _safe_q(request):
    q = (request.GET.get("q") or "").strip()
    return q[:120]


def etapas_autocomplete(request, slug=None):
    banco = get_licenca_db_config(request) or "default"
    empresa = request.session.get("empresa_id")
    q = _safe_q(request)
    limit, offset = _get_pagination(request)

    qs = Etapavisita.objects.using(banco).filter(etap_empr_id=empresa)
    if q:
        qs = qs.filter(Q(etap_descricao__icontains=q) | Q(etap_nume__iexact=q))
    qs = qs.only("etap_id", "etap_nume", "etap_descricao").order_by("etap_descricao")[offset:offset+limit]

    data = [
        {
            "value": e.etap_id,
            "label": f"{e.etap_descricao} • Nº {e.etap_nume}",
            "etap_id": e.etap_id,
            "etap_nume": e.etap_nume,
            "etap_descricao": e.etap_descricao,
        }
        for e in qs
    ]
    return JsonResponse(data, safe=False)


def clientes_autocomplete(request, slug=None):
    banco = get_licenca_db_config(request) or "default"
    empresa = request.session.get("empresa_id")
    q = _safe_q(request)
    limit, offset = _get_pagination(request)

    qs = Entidades.objects.using(banco).filter(enti_empr=empresa, enti_tipo_enti__in=["CL", "AM"])
    if q:
        qs = qs.filter(Q(enti_nome__icontains=q) | Q(enti_cnpj__icontains=q) | Q(enti_cpf__icontains=q))
    qs = qs.only("enti_clie", "enti_nome", "enti_cnpj", "enti_cpf").order_by("enti_nome")[offset:offset+limit]

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


def vendedores_autocomplete(request, slug=None):
    banco = get_licenca_db_config(request) or "default"
    empresa = request.session.get("empresa_id")
    q = _safe_q(request)
    limit, offset = _get_pagination(request)

    qs = Entidades.objects.using(banco).filter(enti_empr=empresa, enti_tipo_enti__in=["VE", "FU", "AM"])
    if q:
        qs = qs.filter(Q(enti_nome__icontains=q) | Q(enti_cnpj__icontains=q) | Q(enti_cpf__icontains=q))
    qs = qs.only("enti_clie", "enti_nome", "enti_cnpj", "enti_cpf").order_by("enti_nome")[offset:offset+limit]

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
    q = _safe_q(request)
    limit, offset = _get_pagination(request)

    qs = Produtos.objects.using(banco).filter(prod_empr=empresa)
    if q:
        qs = qs.filter(
            Q(prod_nome__icontains=q) | Q(prod_codi__iexact=q) | Q(prod_codi_nume__iexact=q) | Q(prod_coba__iexact=q)
        )
    qs = qs.only("prod_codi", "prod_nome", "prod_coba").order_by("prod_nome")[offset:offset+limit]

    data = [
        {
            "value": p.prod_codi,
            "label": f"{p.prod_nome} • COD: {p.prod_codi}{(' • REF: ' + p.prod_coba) if p.prod_coba else ''}",
            "prod_codi": p.prod_codi,
            "prod_nome": p.prod_nome,
            "prod_coba": getattr(p, "prod_coba", None),
        }
        for p in qs
    ]
    return JsonResponse(data, safe=False)

