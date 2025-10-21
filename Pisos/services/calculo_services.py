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

    # Derivar m2 por caixa e peças por caixa a partir do modelo de Produtos
    prod_m2cx_attr = getattr(produto, "prod_cera_m2cx", None)
    m2_por_caixa = parse_decimal(prod_m2cx_attr or 0)
    prod_cera_pccx_attr = getattr(produto, "prod_cera_pccx", None)
    pc_por_caixa = parse_decimal(prod_cera_pccx_attr or 0)
    tem_caixa = m2_por_caixa > 0
    tem_pc = pc_por_caixa > 0

    metragem_com_perda = metragem * (Decimal(1) - perda)

    # PRIORIZAR PEÇAS: Se tem peças E metros quadrados, usar peças primeiro
    if tem_pc:
        # Para produtos com peças por caixa, calcular caixas baseado na metragem em m²
        # mas usar m2_por_caixa para calcular quantas caixas são necessárias
        if tem_caixa:
            # Usar m2_por_caixa para calcular caixas necessárias
            caixas_necessarias = math.ceil(metragem_com_perda / m2_por_caixa)
        else:
            # Se não tem m2_por_caixa, usar pc_por_caixa como fallback
            caixas_necessarias = math.ceil(metragem_com_perda / pc_por_caixa)
        
        print(f"Service: Metragem com perda: {metragem_com_perda}")
        print(f"Service: Peças por caixa: {pc_por_caixa}")
        print(f"Service: M2 por caixa: {m2_por_caixa}")
        print(f"Service: Caixas necessárias: {caixas_necessarias}")
        # Quantidade real em PEÇAS = caixas × peças por caixa
        metragem_real = caixas_necessarias * pc_por_caixa
        print(f"Service: Quantidade real (peças): {metragem_real}")
    elif tem_caixa:
        caixas_necessarias = math.ceil(metragem_com_perda / m2_por_caixa)
        print(f"Service: Metragem com perda: {metragem_com_perda}")
        print(f"Service: Metragem por caixa: {m2_por_caixa}")
        print(f"Service: Caixas necessárias: {caixas_necessarias}")
        metragem_real = caixas_necessarias * m2_por_caixa
        print(f"Service: Metragem real (m2): {metragem_real}")
    else:
        caixas_necessarias = None
        metragem_real = metragem_com_perda

    # Total baseado na metragem real calculada
    total = metragem_real * preco_unit
    print(f"Service: Preço unitário: {preco_unit}")
    print(f"Service: Total: {total}")

    return {
        "metragem_com_perda": arredondar(metragem_com_perda, 2),
        "caixas_necessarias": caixas_necessarias,
        "metragem_real": arredondar(metragem_real, 2),
        "total": arredondar(total),
        "m2_por_caixa": arredondar(m2_por_caixa, 2) if tem_caixa else None,
        "pc_por_caixa": arredondar(pc_por_caixa, 2) if tem_pc else None,
    }


def calcular_ambientes(itens):
    """Agrupa itens por ambiente e soma totais.
    Usa o subtotal já calculado (item_suto) para evitar recálculos incorretos.
    """
    agrupado = defaultdict(lambda: {"total": Decimal("0.00"), "m2_total": Decimal("0.00"), "count": 0})

    for item in itens:
        amb = item.item_ambi or 0
        # Usar o subtotal já calculado (item_suto) em vez de recalcular
        item_subtotal = parse_decimal(getattr(item, 'item_suto', 0))
        item_m2 = parse_decimal(getattr(item, 'item_m2', 0))
        
        agrupado[amb]["total"] += item_subtotal
        agrupado[amb]["m2_total"] += item_m2
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
