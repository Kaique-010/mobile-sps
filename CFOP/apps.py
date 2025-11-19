from django.apps import AppConfig


class CfopConfig(AppConfig):
    name = 'CFOP'
    def ready(self):
        try:
            from .services.suggestion_service import refresh_all_periodic
            refresh_all_periodic()
        except Exception:
            pass
