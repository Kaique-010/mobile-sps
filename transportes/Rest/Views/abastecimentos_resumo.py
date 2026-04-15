from django.http import JsonResponse

from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.services.abastecimentos_resumo_service import AbastecimentosResumoService


def abastecimentos_resumo(request, slug=None):
    banco = get_db_from_slug(slug) if slug else get_licenca_db_config(request)
    empresa_id = request.session.get("empresa_id")
    filial_id = request.session.get("filial_id") or 1

    frota_id = (request.GET.get("abas_frot") or request.GET.get("frota_id") or "").strip()
    veic_sequ = (request.GET.get("abas_veic_sequ") or request.GET.get("veiculo_sequ") or "").strip()
    limit = (request.GET.get("limit") or "10").strip()

    try:
        limit_int = int(limit)
    except Exception:
        limit_int = 10

    veiculo_sequ = None
    if veic_sequ:
        try:
            veiculo_sequ = int(veic_sequ)
        except Exception:
            veiculo_sequ = None

    if not empresa_id:
        return JsonResponse({"results": []})

    data = AbastecimentosResumoService.listar_ultimos(
        banco=banco,
        empresa_id=int(empresa_id),
        filial_id=int(filial_id) if filial_id else None,
        frota_id=frota_id or None,
        veiculo_sequ=veiculo_sequ,
        limit=limit_int,
    )
    ultimo_horimetro = None
    if data:
        ultimo_horimetro = data[0].get("horimetro")
    return JsonResponse({"results": data, "ultimo_horimetro": ultimo_horimetro})
