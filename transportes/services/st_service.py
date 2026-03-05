from transportes.models import RegraICMS
from CFOP.models import CFOP
from decimal import Decimal

class STService:

    def __init__(self, empresa, operacao):
        self.empresa = empresa
        self.operacao = operacao

    def calcular(self, base_calculo, icms_valor, cfop: CFOP):
        if not cfop or not cfop.cfop_gera_st:
            return None

        regra = self._buscar_regra(cfop)
        if not regra:
            return None

        # ST exige MVA ou Pauta (aqui simplificado para MVA)
        if not regra.mva_st and not regra.aliquota_st:
            return None

        base_st = Decimal(base_calculo)

        # Adiciona IPI à base ST se configurado no CFOP
        if cfop.cfop_st_base_inclui_ipi and hasattr(self.operacao, 'valor_ipi') and self.operacao.valor_ipi:
            base_st += Decimal(self.operacao.valor_ipi)

        # Redução base ST
        if regra.reducao_base_st:
             base_st = base_st * (1 - regra.reducao_base_st / 100)

        # Aplica MVA
        if regra.mva_st:
            base_st = base_st * (1 + regra.mva_st / 100)

        # Calcula ICMS ST
        # ST = (Base ST * Alíquota ST) - ICMS Próprio
        icms_st_bruto = base_st * (regra.aliquota_st / 100)
        
        icms_proprio = Decimal(icms_valor) if icms_valor else Decimal(0)
        
        valor_st = icms_st_bruto - icms_proprio
        
        if valor_st < 0:
            valor_st = Decimal(0)

        return {
            "base_st": round(base_st, 2),
            "valor_st": round(valor_st, 2),
            "aliquota_st": regra.aliquota_st,
            "mva_st": regra.mva_st
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
