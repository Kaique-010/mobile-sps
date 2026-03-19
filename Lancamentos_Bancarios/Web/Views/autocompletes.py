from django.db.models import Q
from django.http import JsonResponse

from core.utils import get_licenca_db_config


def autocomplete_bancos(request, slug=None):
    banco = get_licenca_db_config(request) or "default"
    empresa_id = request.session.get("empresa_id")
    term = (request.GET.get("term") or request.GET.get("q") or "").strip()

    from Entidades.models import Entidades

    qs = Entidades.objects.using(banco).filter(
        enti_empr=str(empresa_id),
        enti_tien__in=["B", "C"],
    )

    if term:
        if term.isdigit():
            qs = qs.filter(enti_clie__icontains=term)
        else:
            qs = qs.filter(Q(enti_nome__icontains=term) | Q(enti_fant__icontains=term))

    qs = qs.order_by("enti_nome")[:20]
    data = [{"id": str(obj.enti_clie), "text": f"{obj.enti_clie} - {obj.enti_nome}"} for obj in qs]
    return JsonResponse({"results": data})


def autocomplete_centrosdecustos(request, slug=None):
    banco = get_licenca_db_config(request) or "default"
    empresa_id = request.session.get("empresa_id")
    term = (request.GET.get("term") or request.GET.get("q") or "").strip()

    from CentrodeCustos.models import Centrodecustos

    qs = Centrodecustos.objects.using(banco).filter(cecu_anal="A")
    if empresa_id:
        qs = qs.filter(cecu_empr=int(empresa_id))

    if term:
        qs = qs.filter(Q(cecu_redu__icontains=term) | Q(cecu_nome__icontains=term))

    qs = qs.order_by("cecu_redu")[:30]
    data = [{"id": str(obj.cecu_redu), "text": f"{obj.cecu_redu} - {obj.cecu_nome}"} for obj in qs]
    return JsonResponse({"results": data})


def autocomplete_entidades(request, slug=None):
    banco = get_licenca_db_config(request) or "default"
    empresa_id = request.session.get("empresa_id")
    term = (request.GET.get("term") or request.GET.get("q") or "").strip()

    from Entidades.models import Entidades

    qs = Entidades.objects.using(banco).filter(enti_empr=str(empresa_id))

    if term:
        if term.isdigit():
            qs = qs.filter(enti_clie__icontains=term)
        else:
            qs = qs.filter(Q(enti_nome__icontains=term) | Q(enti_fant__icontains=term))

    qs = qs.order_by("enti_nome")[:20]
    data = [{"id": str(obj.enti_clie), "text": f"{obj.enti_clie} - {obj.enti_nome}"} for obj in qs]
    return JsonResponse({"results": data})

