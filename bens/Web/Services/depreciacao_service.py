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
        Considera pro-rata dia.
        """
        if not valor_aquisicao or not taxa_anual or not data_inicio or not data_fim:
            return Decimal('0')
        
        # Garante tipos corretos
        if not isinstance(valor_aquisicao, Decimal):
             valor_aquisicao = Decimal(str(valor_aquisicao))
             
        if not isinstance(taxa_anual, Decimal):
             taxa_anual = Decimal(str(taxa_anual))

        if data_fim < data_inicio:
            return Decimal('0')

        # Diferença em dias
        dias = (data_fim - data_inicio).days
        
        # Taxa diária derivada da anual (taxa_anual é percentual, ex: 10 para 10%)
        # Taxa diária percentual = taxa_anual / 365
        # Valor diário = valor_aquisicao * (taxa_diaria / 100)
        # Valor total = Valor diário * dias
        
        taxa_dia_perc = taxa_anual / Decimal('365')
        valor_dia = valor_aquisicao * (taxa_dia_perc / Decimal('100'))
        
        depreciacao = valor_dia * Decimal(dias)
        
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
            
        if not isinstance(valor_aquisicao, Decimal):
            valor_aquisicao = Decimal(str(valor_aquisicao))
            
        return (valor_aquisicao - depreciacao_acumulada).quantize(Decimal('0.01'))
        
    @classmethod
    def processar_lista_bens(cls, bens_queryset, data_referencia):
        """
        Processa uma queryset de bens e adiciona os atributos calculados:
        - depreciacao_acumulada
        - valor_atual
        - dias_depreciados
        """
        bens_calculados = []
        total_aquisicao = Decimal('0')
        total_depreciacao = Decimal('0')
        total_atual = Decimal('0')
        
        if not data_referencia:
            data_referencia = date.today()
            
        for bem in bens_queryset:
            # Garante que campos essenciais existam
            if not bem.bens_valo_aqui or not bem.bens_inic_depr or not bem.bens_depr_ano:
                bem.depreciacao_acumulada = Decimal('0.00')
                bem.valor_atual = bem.bens_valo_aqui or Decimal('0.00')
                bem.dias_depreciados = 0
            else:
                depr = cls.calcular_depreciacao_acumulada(
                    valor_aquisicao=bem.bens_valo_aqui,
                    taxa_anual=bem.bens_depr_ano,
                    data_inicio=bem.bens_inic_depr,
                    data_fim=data_referencia
                )
                bem.depreciacao_acumulada = depr
                bem.valor_atual = cls.calcular_valor_atual(bem.bens_valo_aqui, depr)
                bem.dias_depreciados = max(0, (data_referencia - bem.bens_inic_depr).days)
            
            total_aquisicao += bem.bens_valo_aqui or Decimal('0')
            total_depreciacao += bem.depreciacao_acumulada
            total_atual += bem.valor_atual
            
            bens_calculados.append(bem)
            
        return {
            'bens': bens_calculados,
            'total_aquisicao': total_aquisicao,
            'total_depreciacao': total_depreciacao,
            'total_atual': total_atual,
            'data_referencia': data_referencia
        }
