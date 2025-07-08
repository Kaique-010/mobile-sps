from django.apps import AppConfig


class ParametrosAdminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'parametros_admin'
    verbose_name = 'Parâmetros Administrativos'
    
    def ready(self):
        # Importar signals se necessário
        try:
            from . import signals
        except ImportError:
            pass
