from django.http import JsonResponse
from ..aplicacao.emissao_service import EmissaoService
from core.utils import get_db_from_slug

def emitir_nota(request, slug, nota_id):
    db = get_db_from_slug(slug)
    service = EmissaoService(slug, db)
    resposta = service.emitir(nota_id)
    return JsonResponse(resposta)
