import logging
from collections import defaultdict

from ..models import Produtos
from ..utils.etiquetas import formatar_dados_etiqueta
from .grade_service import GradeService

logger = logging.getLogger(__name__)


def gerar_dados_etiquetas(
    banco,
    empresa_id,
    filial_id,
    produtos_ids,
):
    """
    Gera os dados para impressão de etiquetas
    de uma lista de produtos.
    """

    logger.info(
        "Gerando etiquetas para empresa: %s",
        empresa_id,
    )

    produtos = (
        Produtos.objects.using(banco)
        .filter(
            prod_codi__in=produtos_ids,
            prod_empr=empresa_id,
        )
        .select_related("prod_marc")
    )

    if not produtos.exists():
        return []

    grade_service = GradeService(
        banco=banco,
        empresa_id=empresa_id,
        filial_id=filial_id,
    )

    produtos_com_grade = grade_service.listar_produtos_com_grade(
        produtos.values_list("prod_codi", flat=True)
    )

    grades_por_produto = defaultdict(list)

    for grade in produtos_com_grade:
        grades_por_produto[grade.grad_prod].append({
            "item_id": grade.grad_item,
            "descricao": grade.grad_desc,
            "tamanho": grade.grad_nume,
            "cor": grade.grad_cor,
            "saldo": grade.grad_sald,
            "quantidade": 0,
        })

    etiquetas = []

    for produto in produtos:
        dados = formatar_dados_etiqueta(produto)

        dados["grade"] = grades_por_produto.get(
            str(produto.prod_codi),
            [],
        )

        dados["tem_grade"] = bool(dados["grade"])

        etiquetas.append(dados)

        logger.info(
            "Etiqueta gerada - Produto: %s, Hash: %s",
            produto.prod_codi,
            dados.get("hash_id"),
        )

    return etiquetas