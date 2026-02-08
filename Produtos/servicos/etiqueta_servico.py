from ..models import Produtos
from ..utils.etiquetas import formatar_dados_etiqueta
import logging

logger = logging.getLogger(__name__)

def gerar_dados_etiquetas(banco, empresa_id, produtos_ids):
    """
    Gera os dados para impressão de etiquetas de uma lista de produtos.
    """
    logger.info(f"Gerando etiquetas para empresa: {empresa_id}")

    produtos = Produtos.objects.using(banco).filter(
        prod_codi__in=produtos_ids,
        prod_empr=empresa_id
    ).select_related('prod_marc')

    if not produtos.exists():
        return []

    etiquetas = []
    for produto in produtos:
        dados = formatar_dados_etiqueta(produto)
        etiquetas.append(dados)
        logger.info(f"Etiqueta gerada - Produto: {produto.prod_codi}, Hash: {dados.get('hash_id')}, URL: {dados.get('qr_code_url')}")

    return etiquetas
