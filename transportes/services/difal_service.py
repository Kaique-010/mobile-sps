from transportes.models import RegraICMS
from CFOP.models import CFOP
from decimal import Decimal

class DIFALService:

    def __init__(self, empresa, operacao):
        self.empresa = empresa
        self.operacao = operacao

    def calcular(self, base_calculo, icms_valor, cfop: CFOP):
        if not cfop or not cfop.cfop_gera_difal:
            return None

        # DIFAL só se aplica a não contribuinte ou consumidor final?
        # Depende da legislação (EC 87/2015) ou DIFAL ST.
        # Aqui assume lógica genérica baseada na flag do CFOP.

        regra = self._buscar_regra(cfop)
        if not regra:
            return None

        if not regra.aliquota_destino:
             # Se não tiver alíquota destino configurada, não calcula
             return None

        base = Decimal(base_calculo)
        
        # Alíquota Interestadual (da origem para destino)
        aliq_interestadual = regra.aliquota
        
        # Alíquota Interna Destino
        aliq_destino = regra.aliquota_destino

        # DIFAL = Base * (AliqDestino - AliqInterestadual)
        # Pode ser cálculo por fora ou por dentro dependendo do estado/ano
        # Assume cálculo simples (EC 87/2015 padrão)
        
        diferencial = aliq_destino - aliq_interestadual
        
        if diferencial <= 0:
            return None
            
        valor_difal = base * (diferencial / 100)
        
        # Partilha (se aplicável, hoje é 100% destino)
        # partilha_destino = valor_difal
        # partilha_origem = 0

        return {
            "base_difal": round(base, 2),
            "valor_difal": round(valor_difal, 2),
            "aliquota_interestadual": aliq_interestadual,
            "aliquota_destino": aliq_destino
        }

    def _buscar_regra(self, cfop):
        # Garante uso do banco correto
        db_alias = self.empresa._state.db or 'default'
        
        qs = RegraICMS.objects.using(db_alias).filter(
            uf_origem=self.operacao.uf_origem,
            uf_destino=self.operacao.uf_destino,
            contribuinte=self.operacao.contribuinte,
            simples_nacional=self.empresa.simples_nacional,
        )
        
        regra_cfop = qs.filter(cfop=cfop.cfop_codi).first()
        if regra_cfop:
            return regra_cfop
            
        regra_geral = qs.filter(cfop__isnull=True).first()
        if regra_geral:
            return regra_geral
            
        return qs.filter(cfop='').first()
