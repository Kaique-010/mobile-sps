import logging
from celery import shared_task
from transportes.models import Cte
from transportes.services.sefaz_gateway import SefazGateway
from core.utils import get_db_from_slug
import time

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=10, default_retry_delay=30)
def consultar_recibo_task(self, cte_id, numero_recibo, db_slug):
    """
    Task para consultar o recibo do lote enviado (processamento assíncrono da SEFAZ).
    Realiza retries automáticos se estiver em processamento.
    """
    try:
        # Configurar conexão com o banco correto
        if db_slug:
            get_db_from_slug(db_slug)
    except Exception as e:
        logger.error(f"Erro ao configurar banco {db_slug} na task: {e}")
        return {"status": "error", "message": f"Erro de conexão: {str(e)}"}

    try:
        cte = Cte.objects.using(db_slug).get(id=cte_id)
        
        gateway = SefazGateway(cte)
        resultado = gateway.consultar_recibo(numero_recibo)
        
        status = resultado.get('status')
        
        if status == 'autorizado':
            # Atualizar CTe com protocolo e status
            cte.protocolo = resultado.get('protocolo')
            cte.status = 'AUT' # Autorizado
            cte.save()
            logger.info(f"CTe {cte_id} autorizado com sucesso. Protocolo: {cte.protocolo}")
            return resultado
            
        elif status == 'rejeitado':
            # Atualizar CTe com erro
            cte.status = 'REJ' # Rejeitado
            # Poderia salvar o motivo em algum campo de observação ou log
            cte.observacoes_fiscais = f"Rejeição: {resultado.get('mensagem')}"
            cte.save()
            logger.warning(f"CTe {cte_id} rejeitado. Motivo: {resultado.get('mensagem')}")
            return resultado
            
        elif status == 'processando' or status == 'recebido':
            # Se ainda está processando, tentar novamente
            logger.info(f"CTe {cte_id} ainda em processamento. Tentativa {self.request.retries + 1}")
            raise self.retry(exc=Exception("Ainda em processamento"))
            
        else:
            logger.error(f"Status desconhecido na consulta do CTe {cte_id}: {status}")
            return resultado

    except Cte.DoesNotExist:
        logger.error(f"CTe {cte_id} não encontrado no banco {db_slug}")
        return {"status": "error", "message": "CTe não encontrado"}
    except Exception as e:
        if "Ainda em processamento" in str(e):
            raise e # Deixa o retry do Celery lidar
        logger.error(f"Erro na consulta do recibo {numero_recibo}: {e}")
        return {"status": "error", "message": str(e)}
