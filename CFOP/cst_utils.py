
from typing import Dict, List, Any
from Licencas.models import Filiais

# --- CONSTANTS ---

CST_ICMS_NORMAL = [
    ("00", "00 - Tributada integralmente"),
    ("10", "10 - Tributada e com cobrança do ICMS por substituição tributária"),
    ("20", "20 - Com redução de base de cálculo"),
    ("30", "30 - Isenta ou não tributada e com cobrança do ICMS por substituição tributária"),
    ("40", "40 - Isenta"),
    ("41", "41 - Não tributada"),
    ("50", "50 - Suspensão"),
    ("51", "51 - Diferimento"),
    ("60", "60 - ICMS cobrado anteriormente por substituição tributária"),
    ("70", "70 - Com redução de base de cálculo e cobrança do ICMS por substituição tributária"),
    ("90", "90 - Outras"),
]

CST_ICMS_SIMPLES = [
    ("101", "101 - Tributada pelo Simples Nacional com permissão de crédito"),
    ("102", "102 - Tributada pelo Simples Nacional sem permissão de crédito"),
    ("103", "103 - Isenção do ICMS no Simples Nacional para faixa de receita bruta"),
    ("201", "201 - Tributada pelo Simples Nacional com permissão de crédito e com cobrança do ICMS por ST"),
    ("202", "202 - Tributada pelo Simples Nacional sem permissão de crédito e com cobrança do ICMS por ST"),
    ("203", "203 - Isenção do ICMS no Simples Nacional para faixa de receita bruta e com cobrança do ICMS por ST"),
    ("300", "300 - Imune"),
    ("400", "400 - Não tributada pelo Simples Nacional"),
    ("500", "500 - ICMS cobrado anteriormente por substituição tributária (substituído) ou por antecipação"),
    ("900", "900 - Outros"),
]

CST_PIS_COFINS = [
    ("01", "01 - Operação Tributável com Alíquota Básica"),
    ("02", "02 - Operação Tributável com Alíquota Diferenciada"),
    ("03", "03 - Operação Tributável com Alíquota por Unidade de Medida de Produto"),
    ("04", "04 - Operação Tributável Monofásica - Revenda a Alíquota Zero"),
    ("05", "05 - Operação Tributável por Substituição Tributária"),
    ("06", "06 - Operação Tributável a Alíquota Zero"),
    ("07", "07 - Operação Isenta da Contribuição"),
    ("08", "08 - Operação sem Incidência da Contribuição"),
    ("09", "09 - Operação com Suspensão da Contribuição"),
    ("49", "49 - Outras Operações de Saída"),
    ("50", "50 - Operação com Direito a Crédito - Vinculada Exclusivamente a Receita Tributada no Mercado Interno"),
    ("51", "51 - Operação com Direito a Crédito - Vinculada Exclusivamente a Receita Não-Tributada no Mercado Interno"),
    ("52", "52 - Operação com Direito a Crédito - Vinculada Exclusivamente a Exportação"),
    ("53", "53 - Operação com Direito a Crédito - Vinculada a Receitas Tributadas e Não-Tributadas no Mercado Interno"),
    ("54", "54 - Operação com Direito a Crédito - Vinculada a Receitas Tributadas no Mercado Interno e de Exportação"),
    ("55", "55 - Operação com Direito a Crédito - Vinculada a Receitas Não Tributadas no Mercado Interno e de Exportação"),
    ("56", "56 - Operação com Direito a Crédito - Vinculada a Receitas Tributadas e Não-Tributadas no Mercado Interno e de Exportação"),
    ("60", "60 - Crédito Presumido - Operação de Aquisição Vinculada Exclusivamente a Receita Tributada no Mercado Interno"),
    ("61", "61 - Crédito Presumido - Operação de Aquisição Vinculada Exclusivamente a Receita Não-Tributada no Mercado Interno"),
    ("62", "62 - Crédito Presumido - Operação de Aquisição Vinculada Exclusivamente a Exportação"),
    ("63", "63 - Crédito Presumido - Operação de Aquisição Vinculada a Receitas Tributadas e Não-Tributadas no Mercado Interno"),
    ("64", "64 - Crédito Presumido - Operação de Aquisição Vinculada a Receitas Tributadas no Mercado Interno e de Exportação"),
    ("65", "65 - Crédito Presumido - Operação de Aquisição Vinculada a Receitas Não-Tributadas no Mercado Interno e de Exportação"),
    ("66", "66 - Crédito Presumido - Operação de Aquisição Vinculada a Receitas Tributadas e Não-Tributadas no Mercado Interno e de Exportação"),
    ("67", "67 - Crédito Presumido - Outras Operações"),
    ("70", "70 - Operação de Aquisição sem Direito a Crédito"),
    ("71", "71 - Operação de Aquisição com Isenção"),
    ("72", "72 - Operação de Aquisição com Suspensão"),
    ("73", "73 - Operação de Aquisição a Alíquota Zero"),
    ("74", "74 - Operação de Aquisição sem Incidência da Contribuição"),
    ("75", "75 - Operação de Aquisição por Substituição Tributária"),
    ("98", "98 - Outras Operações de Entrada"),
    ("99", "99 - Outras Operações"),
]

CST_IPI = [
    ("00", "00 - Entrada com Recuperação de Crédito"),
    ("01", "01 - Entrada Tributada com Alíquota Zero"),
    ("02", "02 - Entrada Isenta"),
    ("03", "03 - Entrada Não-Tributada"),
    ("04", "04 - Entrada Imune"),
    ("05", "05 - Entrada com Suspensão"),
    ("49", "49 - Outras Entradas"),
    ("50", "50 - Saída Tributada"),
    ("51", "51 - Saída Tributada com Alíquota Zero"),
    ("52", "52 - Saída Isenta"),
    ("53", "53 - Saída Não-Tributada"),
    ("54", "54 - Saída Imune"),
    ("55", "55 - Saída com Suspensão"),
    ("99", "99 - Outras Saídas"),
]

CST_IBS_CBS = [
    ("1", "1 - Tributável"),
    ("2", "2 - Isento"),
    ("3", "3 - Imune"),
    ("4", "4 - Suspensão"),
    ("9", "9 - Outros"),
]

# --- SERVICES ---

def get_csts_por_regime(regime: str) -> Dict[str, List[tuple]]:
    """
    Retorna os CSTs aplicáveis para o regime tributário informado.
    Regimes:
    1 - Simples Nacional
    2 - Simples Nacional - excesso de sublimite
    3 - Regime Normal
    """
    regime = str(regime)
    
    # ICMS
    if regime == '3' or regime == '2': # Normal ou Excesso (pode usar normal dependendo da regra, mas geralmente 2 usa CSOSN ou CST normal dependendo da faixa. Assumindo Normal para 2 simplificado, ou checando parametro. Na dúvida, retornamos Normal se 3, Simples se 1. O 2 é hibrido, vamos tratar como Normal para permitir destaque)
        # Nota: Regime 2 no emissores muitas vezes usa CST Normal.
        cst_icms = CST_ICMS_NORMAL
    else:
        cst_icms = CST_ICMS_SIMPLES

    return {
        'icms': cst_icms,
        'ipi': CST_IPI,
        'pis': CST_PIS_COFINS,
        'cofins': CST_PIS_COFINS,
        'ibs': CST_IBS_CBS,
        'cbs': CST_IBS_CBS,
    }

def get_filial_regime(empresa_id: int, filial_id: int, banco: str = 'default') -> str:
    """
    Busca o regime tributário da filial.
    """
    try:
        f = Filiais.objects.using(banco).filter(empr_empr=empresa_id, empr_codi=filial_id).first()
        if f:
            return str(f.empr_regi_trib or '3') # Default Normal se vazio
    except Exception:
        pass
    return '3'

def get_filial_csts(empresa_id: int, filial_id: int, banco: str = 'default') -> Dict[str, Any]:
    """
    Retorna estrutura completa de CSTs para a filial.
    """
    regime = get_filial_regime(empresa_id, filial_id, banco)
    csts = get_csts_por_regime(regime)
    
    return {
        'empresa_id': empresa_id,
        'filial_id': filial_id,
        'regime': regime,
        'csts': csts
    }

def export_csts_to_dict(empresa_id: int, filial_id: int, banco: str = 'default') -> Dict[str, Any]:
    """
    Gera o dicionário estruturado solicitado (arquivo de auxílio).
    """
    data = get_filial_csts(empresa_id, filial_id, banco)
    
    # Formata para JSON friendly (lista de dicts em vez de tuplas)
    formatted_csts = {}
    for tributo, lista in data['csts'].items():
        formatted_csts[tributo] = [{'codigo': k, 'descricao': v} for k, v in lista]
        
    return {
        'metadata': {
            'empresa': empresa_id,
            'filial': filial_id,
            'regime_codigo': data['regime'],
            'regime_descricao': 'Simples Nacional' if data['regime'] == '1' else 'Regime Normal' if data['regime'] == '3' else 'Simples Nacional - Excesso'
        },
        'tributos': formatted_csts
    }
