import logging
import time
from django.db import connections
from django.conf import settings
from decouple import config
from core.licenca_context import LICENCAS_MAP

logger = logging.getLogger(__name__)

def preload_database_connections():
    """Pré-carrega todas as conexões de banco na inicialização"""
    start_time = time.time()
    logger.info("🔥 Iniciando pré-carregamento de conexões...")
    
    loaded_connections = 0
    
    for licenca in LICENCAS_MAP:
        try:
            slug = licenca["slug"]
            
            # Pular se já existe
            if slug in settings.DATABASES:
                continue
                
            # Configurar conexão
            prefixo = slug.upper()
            db_user = config(f"{prefixo}_DB_USER", default=None)
            db_password = config(f"{prefixo}_DB_PASSWORD", default=None)
            
            if not db_user or not db_password:
                logger.warning(f"⚠️  Credenciais não encontradas para {slug}")
                continue
            
            settings.DATABASES[slug] = {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': licenca["db_name"],
                'USER': db_user,
                'PASSWORD': db_password,
                'HOST': licenca["db_host"],
                'PORT': licenca["db_port"],
                'OPTIONS': {
                    'options': '-c timezone=America/Araguaina',
                    'connect_timeout': 10,
                    'application_name': 'mobile_sps_preload',
                },
                'CONN_MAX_AGE': 600,  # 10 minutos
                'CONN_HEALTH_CHECKS': True,
            }
            
            # Preparar conexão
            connections.ensure_defaults(slug)
            connections.prepare_test_settings(slug)
            
            # Testar conexão
            conn = connections[slug]
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                
            loaded_connections += 1
            logger.info(f"✅ Conexão {slug} pré-carregada")
            
        except Exception as e:
            logger.error(f"❌ Erro ao pré-carregar {slug}: {e}")
    
    total_time = (time.time() - start_time) * 1000
    logger.info(f"🚀 Pré-carregamento concluído: {loaded_connections} conexões em {total_time:.2f}ms")
    
    return loaded_connections