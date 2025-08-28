from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        """Executado quando Django termina de carregar"""
        try:
            from .connection_preloader import preload_database_connections
            preload_database_connections()
        except Exception as e:
            logger.error(f"Erro no pré-carregamento: {e}")