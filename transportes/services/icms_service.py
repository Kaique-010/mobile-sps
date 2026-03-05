from transportes.models import RegraICMS
from CFOP.models import CFOP
from decimal import Decimal

class ICMSCalculationService:

    def __init__(self, empresa, operacao):
        self.empresa = empresa
        self.operacao = operacao

    def calcular(self, base_calculo, cfop: CFOP):
        if not cfop or not cfop.cfop_exig_icms:
            return None

        regra = self._buscar_regra(cfop)
        if not regra:
             # Se não achar regra, retorna None ou levanta erro?
             # Por enquanto retorna None, o usuário terá que preencher manual
             return None

        if regra.isento:
            return {
                "cst": regra.csosn if regra.simples_nacional else regra.cst,
                "base": Decimal(0),
                "aliquota": Decimal(0),
                "valor": Decimal(0),
                "reducao": Decimal(0)
            }
        
        # Converte para Decimal para evitar erros de precisão
        base = Decimal(base_calculo)
        aliquota = regra.aliquota
        reducao = regra.reducao_base
        
        base_reduzida = base
        if reducao:
            base_reduzida = base * (1 - reducao / 100)

        valor_icms = base_reduzida * (aliquota / 100)

        return {
            "cst": regra.csosn if regra.simples_nacional else regra.cst,
            "base": round(base_reduzida, 2),
            "aliquota": aliquota,
            "valor": round(valor_icms, 2),
            "reducao": reducao
        }

    def _buscar_regra(self, cfop):
        # Garante uso do banco correto
        db_alias = self.empresa._state.db or 'default'
        
        # 1. Tenta regra específica para o CFOP
        qs = RegraICMS.objects.using(db_alias).filter(
            uf_origem=self.operacao.uf_origem,
            uf_destino=self.operacao.uf_destino,
            contribuinte=self.operacao.contribuinte,
            simples_nacional=self.empresa.simples_nacional,
        )
        
        # Tenta achar com CFOP específico
        regra_cfop = qs.filter(cfop=cfop.cfop_codi).first()
        if regra_cfop:
            return regra_cfop
            
        # 2. Tenta regra geral (sem CFOP)
        regra_geral = qs.filter(cfop__isnull=True).first()
        if regra_geral:
            return regra_geral
            
        # 3. Tenta regra geral (CFOP vazio string)
        regra_geral_vazio = qs.filter(cfop='').first()
        
        return regra_geral_vazio
