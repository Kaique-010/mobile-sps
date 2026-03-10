from django.http import JsonResponse
from django.views.decorators.http import require_POST
from ..services.calculo_impostos_service import CalculoImpostosService
from ..models import Nota
from ..services.nota_service import NotaService
from core.utils import get_db_from_slug
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

@api_view(['POST'])
def calcular_impostos(request, slug, nota_id):
    try:
        db = get_db_from_slug(slug)
        nota = Nota.objects.using(db).get(pk=nota_id)
        
        service = CalculoImpostosService(db)
        # Apply taxes (updates items in DB)
        service.aplicar_impostos(nota)
        
        # Update totals in Nota object (DB)
        NotaService.atualizar_totais(nota)
        
        return JsonResponse({
            "mensagem": "Cálculo realizado com sucesso",
            "total_nota": str(nota.total) if hasattr(nota, 'total') else "0.00",
        })
    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=400)
