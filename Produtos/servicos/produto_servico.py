from ..models import Produtos
from ..utils.hash import gerar_hash_str
import logging

logger = logging.getLogger(__name__)

def buscar_produto_por_hash(banco, hash_busca, empresa_id_preferencia=None):
    """
    Tenta encontrar um produto através do hash do QR Code.
    Primeiro busca na empresa de preferência, depois faz busca global se necessário (para diagnóstico).
    Retorna o código do produto se encontrar.
    """
    
    # 1. Busca na empresa de preferência (Otimizada)
    if empresa_id_preferencia:
        candidatos = Produtos.objects.using(banco).filter(
            prod_empr=empresa_id_preferencia
        ).values('prod_empr', 'prod_codi')
        
        for cand in candidatos:
            gen_hash = gerar_hash_str(cand['prod_empr'], cand['prod_codi'])
            if str(gen_hash).strip().lower() == str(hash_busca).strip().lower():
                logger.info(f"MATCH ENCONTRADO! Produto: {cand['prod_codi']}")
                return cand['prod_codi']
        
        logger.warning(f"Nenhum produto corresponde ao hash {hash_busca} na empresa {empresa_id_preferencia}")

    # 2. Busca Global para Diagnóstico (Opcional, pode ser removido se for custoso)
    logger.info("Iniciando busca global de hash para diagnóstico...")
    all_cands = Produtos.objects.using(banco).all().values('prod_empr', 'prod_codi')
    for cand in all_cands:
        g_hash = gerar_hash_str(cand['prod_empr'], cand['prod_codi'])
        if str(g_hash).strip().lower() == str(hash_busca).strip().lower():
            logger.error(f"DIAGNÓSTICO CRÍTICO: O hash {hash_busca} pertence à Empresa {cand['prod_empr']} (Produto {cand['prod_codi']}). O usuário está na Empresa {empresa_id_preferencia}.")
            # Não retornamos o produto de outra empresa por segurança, apenas logamos
            return None

    return None
