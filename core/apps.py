from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        """Executado quando o Django está pronto"""
        # Importar aqui para evitar circular imports
        import os
        
        # Só executar no processo principal (não nos workers)
        if os.environ.get('RUN_MAIN') != 'true':
            return
            
        logger.info("🚀 Core app inicializado")
        
        # REMOVIDO: pré-carregamento de conexões (causa do delay)
        # try:
        #     from .connection_preloader import preload_database_connections
        #     preload_database_connections()
        # except Exception as e:
        #     logger.error(f"Erro no pré-carregamento: {e}")
        
        logger.info("✅ Core inicializado SEM pré-carregamento de conexões")
