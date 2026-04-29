# views/calcular_item_view.py
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from Produtos.models import Produtos
from Pisos.services.calculo_services import calcular_item
from core.utils import get_db_from_slug

@require_POST
def api_calcular_item(request, slug):
    banco = get_db_from_slug(slug)
    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({"erro": "JSON inválido"}, status=400)

    class ItemProxy:
        item_m2 = body.get("item_m2") or 0
        item_queb = body.get("item_queb") or 0
        item_unit = body.get("item_unit") or 0

    prod_id = body.get("item_prod")
    produto = None
    if prod_id:
        produto = Produtos.objects.using(banco).filter(prod_codi=prod_id).first()

    resultado = calcular_item(ItemProxy(), produto=produto)

    return JsonResponse({
        "caixas": str(resultado["caixas_necessarias"] or 0),
        "quantidade": str(resultado["metragem_real"]),
        "total": str(resultado["total"]),
        "m2_por_caixa": str(resultado["m2_por_caixa"] or 0),
        "pc_por_caixa": str(resultado["pc_por_caixa"] or 0),
    })