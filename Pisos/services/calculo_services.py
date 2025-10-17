# services/calculo_service.py
from .utils_service import parse_decimal, arredondar
from decimal import Decimal, ROUND_HALF_UP
import math
from collections import defaultdict

def calcular_item(item, produto=None):
    """Cálculo físico base: quantidades e totais brutos.
    Usa dados do produto para calcular caixas quando disponível.
    """
    metragem = parse_decimal(item.item_m2 or 0)
    perda = parse_decimal(item.item_queb or 0) / Decimal(100)
    preco_unit = parse_decimal(item.item_unit or 0)

    # Derivar m2 por caixa a partir do modelo de Produtos
    prod_m2cx_attr = getattr(produto, "prod_cera_m2cx", None)
    m2_por_caixa = parse_decimal(prod_m2cx_attr or 0)
    tem_caixa = m2_por_caixa > 0

    metragem_com_perda = metragem * (Decimal(1) + perda)

    if tem_caixa:
        caixas_necessarias = math.ceil(metragem_com_perda / m2_por_caixa)
        metragem_real = caixas_necessarias * m2_por_caixa
    else:
        caixas_necessarias = None
        metragem_real = metragem_com_perda

    # Importante: total sempre por m² (alinha com views.calcular_metragem)
    total = metragem_real * preco_unit

    return {
        "metragem_com_perda": arredondar(metragem_com_perda, 2),
        "caixas_necessarias": caixas_necessarias,
        "metragem_real": arredondar(metragem_real, 2),
        "total": arredondar(total),
        "m2_por_caixa": arredondar(m2_por_caixa, 2) if tem_caixa else None,
    }


def calcular_ambientes(itens):
    """Agrupa itens por ambiente e soma totais.
    Usa o cálculo local para manter consistência de preço por m².
    """
    agrupado = defaultdict(lambda: {"total": Decimal("0.00"), "m2_total": Decimal("0.00"), "count": 0})

    for item in itens:
        calc = calcular_item(item)
        amb = item.item_ambi or 0
        agrupado[amb]["total"] += calc["total"]
        agrupado[amb]["m2_total"] += calc["metragem_com_perda"]
        agrupado[amb]["count"] += 1

    return [
        {
            "ambiente": amb,
            "total_ambiente": arredondar(data["total"]),
            "m2_total": arredondar(data["m2_total"], 2),
            "qtd_itens": data["count"]
        }
        for amb, data in agrupado.items()
    ]

def calcular_total_geral(ambientes):
    """Soma todos os ambientes."""
    return sum(parse_decimal(amb["total_ambiente"]) for amb in ambientes)
