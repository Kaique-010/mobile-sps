from django.urls import reverse
from .constants import ONBOARDING_STEPS
from .models import OnboardingStepProgress
from Licencas.models import Usuarios
from core.utils import get_licenca_db_config
from django.db import connections


def get_onboarding_state(user, empresa_id, db_alias: str | None = None):
    if not user.is_authenticated or not empresa_id:
        steps_with_status = []
        for step in sorted(ONBOARDING_STEPS, key=lambda s: s["ordem"]):
            steps_with_status.append({
                "slug": step["slug"],
                "nome": step["nome"],
                "ordem": step["ordem"],
                "url": "#",
                "completed": False,
            })
        next_step = steps_with_status[0] if steps_with_status else None
        return {"steps": steps_with_status, "next_step": next_step, "all_done": False}

    qs = OnboardingStepProgress.objects
    if db_alias:
        qs = qs.using(db_alias)

    # Evitar 500 se tabela não existir no banco atual
    try:
        alias = db_alias or 'default'
        conn = connections[alias]
        if 'onboarding_step_progress' not in conn.introspection.table_names():
            done_slugs = set()
        else:
            done_slugs = set(
                qs.filter(usuario=user, empr_id=empresa_id)
                  .values_list("step_slug", flat=True)
            )
    except Exception:
        done_slugs = set()

    steps_with_status = []
    next_step = None

    for step in sorted(ONBOARDING_STEPS, key=lambda s: s["ordem"]):
        completed = step["slug"] in done_slugs
        data = {
            "slug": step["slug"],
            "nome": step["nome"],
            "ordem": step["ordem"],
            "url": "#",   
            "completed": completed,
        }
        steps_with_status.append(data)
        if not completed and next_step is None:
            next_step = data

    return {
        "steps": steps_with_status,
        "next_step": next_step,
        "all_done": next_step is None,
    }

def mark_step_done(user, empresa_id, step_slug, db_alias: str | None = None):
    print("=== DEBUG ONBOARDING ===")
    print("User:", user, type(user))
    print("Authenticated:", user.is_authenticated)
    print("empresa_id:", empresa_id)
    print("step_slug:", step_slug)
    print("db_alias:", db_alias)

    if not user.is_authenticated or not empresa_id:
        return

    qs = OnboardingStepProgress.objects
    if db_alias:
        qs = qs.using(db_alias)

    qs.get_or_create(
        usuario=user,
        empr_id=empresa_id,
        step_slug=step_slug
    )
