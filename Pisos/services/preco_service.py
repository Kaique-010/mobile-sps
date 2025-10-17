# services/preco_service.py
from decimal import Decimal
import logging
from django.db import connections
from django.db.utils import ProgrammingError
from Produtos.models import Tabelaprecos, Produtos
from .utils_service import parse_decimal

logger = logging.getLogger(__name__)

def get_preco_produto(banco, produto_id, condicao="0"):
    """
    Busca o preço do produto priorizando ORM e com fallback em SQL cru.
    condicao='0' → à vista | condicao!='0' → a prazo
    """
    preco = None

    # 1️⃣ ORM primeiro (corrige filtro por código em vez de objeto e ordenação)
    try:
        produto = Produtos.objects.using(banco).filter(prod_codi=produto_id).first()
        if not produto:
            logger.warning(f"[preco_service] Produto não encontrado para obter preço: {produto_id}")
        else:
            # tabe_prod é CharField → usar código do produto
            # tabe_empr é IntegerField, enquanto prod_empr é CharField → tentar converter
            try:
                empresa = int(produto.prod_empr) if produto.prod_empr is not None else None
            except Exception:
                empresa = produto.prod_empr

            qs = Tabelaprecos.objects.using(banco).filter(tabe_prod=produto.prod_codi)
            if empresa is not None:
                qs = qs.filter(tabe_empr=empresa)

            # Ordena pelos campos de log se existirem
            qs = qs.order_by("-field_log_data", "-field_log_time")

            preco_entry = qs.first()
            if preco_entry:
                preco = preco_entry.tabe_avis if condicao == "0" else preco_entry.tabe_apra
    except Exception as e:
        # Se os modelos estiverem managed=False ou a estrutura divergir, cai para SQL cru
        logger.debug(f"[preco_service] Falha no ORM ao obter preço: {e}")

    # 2️⃣ Fallback: SQL cru (ajusta ordenação para colunas reais _log_data/_log_time)
    if preco is None:
        try:
            with connections[banco].cursor() as cursor:
                cursor.execute(
                    """
                    SELECT tabe_avis, tabe_apra
                    FROM tabelaprecos
                    WHERE tabe_prod = %s
                    ORDER BY _log_data DESC, _log_time DESC
                    LIMIT 1
                    """,
                    [produto_id],
                )
                row = cursor.fetchone()
                if row:
                    preco = row[0] if condicao == "0" else row[1]
        except ProgrammingError as exc:
            logger.debug(f"[preco_service] Erro SQL ao obter preço: {exc}")
            raise ValueError("Tabela de preços não encontrada no banco.")

    if preco is None:
        raise ValueError(f"Produto {produto_id} não possui preço definido")

    return parse_decimal(preco)
