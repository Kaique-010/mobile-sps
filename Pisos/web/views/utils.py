from django.http import JsonResponse
from core.utils import get_db_from_slug
from Entidades.models import Entidades


def autocomplete_entidades(request, slug, tipo="clientes"):
    banco = get_db_from_slug(slug)
    q = (request.GET.get("term") or "").strip()
    qs = Entidades.objects.using(banco).all()
    if q:
        if q.isdigit():
            qs = qs.filter(enti_clie=int(q))
        else:
            qs = qs.filter(enti_nome__icontains=q)
    if tipo == "vendedores":
        qs = qs.filter(enti_tipo__in=["V", "A", "C"]) if hasattr(Entidades, 'enti_tipo') else qs
    data = [{"id": e.enti_clie, "label": f"{e.enti_clie} - {e.enti_nome}", "value": e.enti_clie} for e in qs[:20]]
    return JsonResponse(data, safe=False)


def autocomplete_clientes(request, slug):
    return autocomplete_entidades(request, slug, "clientes")


def autocomplete_vendedores(request, slug):
    return autocomplete_entidades(request, slug, "vendedores")
