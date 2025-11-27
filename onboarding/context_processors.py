
from .services import get_onboarding_state

def onboarding_context(request):
    empresa_id = request.session.get("empresa_id")
    return {"onboarding_state": get_onboarding_state(request.user, empresa_id)}
