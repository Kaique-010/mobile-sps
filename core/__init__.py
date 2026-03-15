default_app_config = 'core.apps.CoreConfig'

try:
    from datetime import timezone as _dt_timezone
    from django.utils import timezone as _dj_timezone

    if not hasattr(_dj_timezone, "utc"):
        _dj_timezone.utc = _dt_timezone.utc
except Exception:
    pass
