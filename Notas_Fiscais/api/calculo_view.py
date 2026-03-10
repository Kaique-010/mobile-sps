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

        debug_data = service.aplicar_impostos(nota, return_debug=True)
        
        NotaService.atualizar_totais(nota)
        
        print("Nota calculada e atualizado o total:", nota.total)
        
        # Print debug data
        print("Debug Calculo Impostos:", debug_data)
        
        return JsonResponse({
            "mensagem": "Cálculo realizado com sucesso",
            "total_nota": str(nota.total) if hasattr(nota, 'total') else "0.00",
            "debug_calculo": debug_data,
        })
    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=400)
