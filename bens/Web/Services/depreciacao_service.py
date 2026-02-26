from decimal import Decimal
from datetime import date
from dateutil.relativedelta import relativedelta

class DepreciacaoService:
    @staticmethod
    def calcular_taxas_depreciacao(vida_util_anos):
        """
        Calcula as taxas de depreciação anual, mensal e diária baseada na vida útil em anos.
        Retorna uma tupla (taxa_ano, taxa_mes, taxa_dia) em percentual (ex: 10.0 para 10%).
        """
        if not vida_util_anos or vida_util_anos <= 0:
            return Decimal('0'), Decimal('0'), Decimal('0')
        
        vida_util_anos = Decimal(vida_util_anos)
        taxa_ano = Decimal('100') / vida_util_anos
        taxa_mes = taxa_ano / Decimal('12')
        taxa_dia = taxa_ano / Decimal('365') # Usando ano comercial ou civil? Geralmente 365 ou 360. Vamos usar 365 para precisão diária simples.
        
        return (
            taxa_ano.quantize(Decimal('0.0001')),
            taxa_mes.quantize(Decimal('0.0001')),
            taxa_dia.quantize(Decimal('0.0001'))
        )

    @staticmethod
    def calcular_depreciacao_acumulada(valor_aquisicao, taxa_anual, data_inicio, data_fim):
        """
        Calcula a depreciação acumulada linear entre a data de início e a data fim.
        Considera pro-rata dia ou mês? Vamos implementar pro-rata dias para maior precisão.
        """
        if not valor_aquisicao or not taxa_anual or not data_inicio or not data_fim:
            return Decimal('0')
        
        if data_fim < data_inicio:
            return Decimal('0')

        # Diferença em dias
        dias = (data_fim - data_inicio).days
        
        # Taxa diária derivada da anual
        taxa_dia = (taxa_anual / Decimal('100')) / Decimal('365')
        
        depreciacao = valor_aquisicao * taxa_dia * Decimal(dias)
        
        # Não pode depreciar mais que o valor de aquisição (assumindo valor residual 0 por enquanto)
        if depreciacao > valor_aquisicao:
            depreciacao = valor_aquisicao
            
        return depreciacao.quantize(Decimal('0.01'))

    @staticmethod
    def calcular_valor_atual(valor_aquisicao, depreciacao_acumulada):
        """
        Calcula o valor contábil atual (Valor de Aquisição - Depreciação Acumulada).
        """
        if valor_aquisicao is None:
            valor_aquisicao = Decimal('0')
        if depreciacao_acumulada is None:
            depreciacao_acumulada = Decimal('0')
            
        return (valor_aquisicao - depreciacao_acumulada).quantize(Decimal('0.01'))
