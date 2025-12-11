import logging
import time
from django.core.cache import cache
from django.db import connections
from core.licenca_context import get_licencas_map
from core.utils import get_db_from_slug

logger = logging.getLogger(__name__)

def warm_modules_cache():
    """Pré-aquece o cache de módulos para todas as licenças"""
    start_time = time.time()
    logger.info("🔥 Iniciando aquecimento do cache de módulos...")
    
    warmed_count = 0
    
    for licenca in get_licencas_map():
        try:
            slug = licenca["slug"]
            
            # Configurar conexão dinamicamente
            banco = get_db_from_slug(slug)
            if not banco:
                logger.warning(f"⚠️  Não foi possível configurar banco para {slug}")
                continue
            
            # Simular empresa_id e filial_id padrão
            empresa_id = 1
            filial_id = 1
            cache_key = f"modulos_licenca_{slug}_{empresa_id}_{filial_id}"
            
            # Verificar se já está em cache
            if cache.get(cache_key) is not None:
                logger.info(f"✅ Cache já existe para {slug}")
                continue
            
            # Buscar módulos do banco
            try:
                from parametros_admin.models import PermissaoModulo
                
                permissoes = PermissaoModulo.objects.using(banco).filter(
                    perm_empr=empresa_id,
                    perm_fili=filial_id,
                    perm_ativ=True,
                    perm_modu__modu_ativ=True
                ).select_related('perm_modu').only(
                    'perm_modu__modu_nome',
                    'perm_modu__modu_ativ'
                )
                
                modulos_disponiveis = [p.perm_modu.modu_nome for p in permissoes]
                
                # Armazenar no cache por 30 minutos
                cache.set(cache_key, modulos_disponiveis, 1800)
                
                warmed_count += 1
                logger.info(f"🔥 Cache aquecido para {slug}: {len(modulos_disponiveis)} módulos")
                
            except Exception as e:
                logger.error(f"❌ Erro ao aquecer cache para {slug}: {e}")
                # Cache vazio para evitar tentativas repetidas
                cache.set(cache_key, [], 300)
                
        except Exception as e:
            logger.error(f"❌ Erro geral ao processar {slug}: {e}")
    
    total_time = (time.time() - start_time) * 1000
    logger.info(f"🔥 Cache warming concluído: {warmed_count} licenças em {total_time:.2f}ms")
    
    return warmed_count

def warm_cache_async():
    """Executa cache warming em background"""
    import threading
    
    def run_warming():
        try:
            warm_modules_cache()
        except Exception as e:
            logger.error(f"❌ Erro no cache warming assíncrono: {e}")
    
    thread = threading.Thread(target=run_warming, daemon=True)
    thread.start()
    logger.info("🔥 Cache warming iniciado em background")
