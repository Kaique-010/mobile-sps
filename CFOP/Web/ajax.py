from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from core.utils import get_licenca_db_config
from ..models import Cfop

@require_http_methods(["GET"])
def validate_unique_code(request, slug=None):
    banco = get_licenca_db_config(request)
    empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
    codi = request.GET.get('codi')
    ok = True
    if empresa_id and codi:
        ok = not Cfop.objects.using(banco).filter(cfop_empr=int(empresa_id), cfop_codi=int(codi)).exists()
    return JsonResponse({'valid': ok})