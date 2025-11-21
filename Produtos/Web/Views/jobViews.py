from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .importador import importar_ibpt_automatico
from core.utils import get_licenca_db_config

@csrf_exempt
def job_importar_ibpt(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
        total = importar_ibpt_automatico(request=request, empresa_id=empresa_id)
        return JsonResponse({"status": "ok", "atualizados": total, "empresa": empresa_id})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
