from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from core.utils import get_licenca_db_config
from ..models import Cfop, CfopSearchHistory
from ..services.suggestion_service import suggest_tax

@require_http_methods(["GET"])
def sugerir_tributacao(request, slug=None):
    banco = get_licenca_db_config(request)
    cfop_code = request.GET.get('cfop')
    state = request.GET.get('uf') or ''
    entity_type = request.GET.get('tipo') or ''
    data = suggest_tax(cfop_code, state, entity_type)
    try:
        empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa')
        usuario_id = getattr(getattr(request, 'user', None), 'usua_codi', None)
        CfopSearchHistory.objects.create(
            empresa_id=int(empresa_id) if empresa_id else None,
            usuario_id=int(usuario_id) if usuario_id else None,
            query=str(cfop_code or ''),
            uf=str(state or ''),
            tipo=str(entity_type or ''),
        )
    except Exception:
        pass
    return JsonResponse(data)

@require_http_methods(["GET"])
def cfop_autocomplete(request, slug=None):
    banco = get_licenca_db_config(request)
    empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
    q = (request.GET.get('q') or '').strip()
    s = Cfop.objects.using(banco).all()
    if empresa_id:
        s = s.filter(cfop_empr=int(empresa_id))
    if q:
        s = s.filter(Q(cfop_desc__icontains=q) | Q(cfop_cfop__icontains=q) | Q(cfop_codi__icontains=q))
    items = [
        {
            'id': f"{o.cfop_empr}:{o.cfop_codi}",
            'text': f"{o.cfop_cfop} - {o.cfop_desc}",
            'cfop': o.cfop_cfop,
            'codi': o.cfop_codi,
            'empr': o.cfop_empr,
        }
        for o in s.order_by('cfop_cfop')[:20]
    ]
    try:
        usuario_id = getattr(getattr(request, 'user', None), 'usua_codi', None)
        CfopSearchHistory.objects.create(
            empresa_id=int(empresa_id) if empresa_id else None,
            usuario_id=int(usuario_id) if usuario_id else None,
            query=str(q or ''),
        )
    except Exception:
        pass
    return JsonResponse({'results': items})