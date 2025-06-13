from django.apps import AppConfig


class AuditoriaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'auditoria'
    verbose_name = 'Auditoria de Ações'
    
    def ready(self):
        # Importar signals para registrá-los
        import auditoria.signals