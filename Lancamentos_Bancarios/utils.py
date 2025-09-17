# utils.py

from .models import Lctobancario
from django.db.models import Max
from datetime import date

def get_next_lcto_number(lcto_empr, lcto_fili, banco):
    """Gera próximo número de lançamento bancário"""
    maior = Lctobancario.objects.using(banco).filter(
        laba_empr=lcto_empr,
        laba_fili=lcto_fili
    ).aggregate(Max('laba_ctrl'))['laba_ctrl__max'] or 0
    return maior + 1

def criar_lancamento_bancario_baixa(empresa, filial, banco_id, valor, historico, entidade, tipo_baixa, banco_db):
    """
    Cria lançamento bancário automático para baixa de títulos
    
    Args:
        empresa: ID da empresa
        filial: ID da filial  
        banco_id: ID do banco
        valor: Valor do lançamento
        historico: Histórico do lançamento
        entidade: ID da entidade (cliente/fornecedor)
        tipo_baixa: 'pagar' ou 'receber'
        banco_db: Nome do banco de dados
    
    Returns:
        Lctobancario: Objeto do lançamento criado
    """
    
    # Gera próximo número de controle
    ctrl_numero = get_next_lcto_number(empresa, filial, banco_db)
    
    # Define débito/crédito baseado no tipo
    # Contas a pagar: débito (saída de dinheiro)
    # Contas a receber: crédito (entrada de dinheiro)
    dbcr = 'D' if tipo_baixa == 'pagar' else 'C'
    
    # Cria o lançamento
    lancamento = Lctobancario.objects.using(banco_db).create(
        laba_empr=empresa,
        laba_fili=filial,
        laba_banc=banco_id,
        laba_ctrl=ctrl_numero,
        laba_data=date.today(),
        laba_valo=valor,
        laba_hist=historico,
        laba_dbcr=dbcr,
        laba_enti=entidade
    )
    
    return lancamento
