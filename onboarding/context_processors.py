
from .services import get_onboarding_state
from core.utils import get_licenca_db_config

def onboarding_context(request):
    empresa_id = request.session.get("empresa_id")
    try:
        banco = get_licenca_db_config(request) or 'default'
    except Exception:
        banco = 'default'
    return {"onboarding_state": get_onboarding_state(request.user, empresa_id, banco)}
