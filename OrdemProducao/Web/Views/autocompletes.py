from django.http import JsonResponse
from core.utils import get_licenca_db_config

from ...services import OrdemProducaoService


def autocomplete_clientes(request, slug=None):
    banco = get_licenca_db_config(request) or "default"
    empresa_id = int(request.session.get("empresa_id") or 1)
    term = (request.GET.get("term") or request.GET.get("q") or "").strip()
    results = OrdemProducaoService.autocomplete_clientes(using=banco, empresa_id=empresa_id, term=term)
    return JsonResponse({"results": results})


def autocomplete_vendedores(request, slug=None):
    banco = get_licenca_db_config(request) or "default"
    empresa_id = int(request.session.get("empresa_id") or 1)
    term = (request.GET.get("term") or request.GET.get("q") or "").strip()
    results = OrdemProducaoService.autocomplete_vendedores(using=banco, empresa_id=empresa_id, term=term)
    return JsonResponse({"results": results})


def autocomplete_produtos(request, slug=None):
    banco = get_licenca_db_config(request) or "default"
    empresa_id = int(request.session.get("empresa_id") or 1)
    term = (request.GET.get("term") or request.GET.get("q") or "").strip()
    results = OrdemProducaoService.autocomplete_produtos(using=banco, empresa_id=empresa_id, term=term)
    return JsonResponse({"results": results})
