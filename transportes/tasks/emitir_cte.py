import logging
from celery import shared_task
from transportes.models import Cte
from transportes.services.emissao_service import EmissaoService

logger = logging.getLogger(__name__)

@shared_task
def emitir_cte_task(cte_id, db_slug):
    """
    Task Celery para emitir o CTe de forma assíncrona.
    Recebe o ID do CTe e o slug do banco de dados (multitenancy).
    """
    from core.utils import get_db_from_slug
    
    # Configurar conexão com o banco correto
    try:
        if db_slug:
            get_db_from_slug(db_slug)
    except Exception as e:
        logger.error(f"Erro ao configurar banco {db_slug} na task: {e}")
        return {"status": "error", "message": f"Erro de conexão: {str(e)}"}

    try:
        # Buscar o CTe usando o ID (que é CharField) e o banco correto
        cte = Cte.objects.using(db_slug).get(id=cte_id)
        
        service = EmissaoService(cte)
        resultado = service.emitir()
        
        return resultado
    except Cte.DoesNotExist:
        logger.error(f"CTe {cte_id} não encontrado no banco {db_slug}")
        return {"status": "error", "message": "CTe não encontrado"}
    except Exception as e:
        logger.error(f"Erro na emissão do CTe {cte_id}: {e}")
        # Aqui poderia atualizar o status do CTe para ERRO
        return {"status": "error", "message": str(e)}
