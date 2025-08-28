from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import time

@require_http_methods(["GET"])
@csrf_exempt
def health_check(request):
    """Endpoint de verificação de saúde para Docker"""
    return JsonResponse({
        "status": "healthy",
        "timestamp": time.time(),
        "service": "Mobile SPS Backend",
        "version": "1.0.0"
    })