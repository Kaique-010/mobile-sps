from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_HALF_UP
import logging
from dataclasses import replace
from typing import Optional, Dict, Any
from .bases import BasesFiscal, FiscalContexto
from ..models import CFOP, MapaCFOP, TabelaICMS, NCM_CFOP_DIF
from Produtos.models import Produtos, Ncm, NcmAliquota
from .auxiliares import get_empresa_uf_origem, get_regime, ResolverAliquotaPorRegime


logger = logging.getLogger(__name__)


class ResolverCST:
    """
    Centraliza a lógica de decisão de CST/CSOSN (Clean Architecture).
    Determina o código de situação tributária baseado no regime e regras.
    """
    
    # Defaults
    CST_ICMS_DEFAULT = "00" 
    CSOSN_DEFAULT = "101"
    CST_IPI_DEFAULT = "50" # Saída Tributada
    CST_PIS_COFINS_DEFAULT = "01" # Operação Tributável
    
    @classmethod
    def resolver_icms(cls, ctx: FiscalContexto) -> str:
        # 1. Override explícito do cadastro (Produto/Fiscal)
        if ctx.fiscal_padrao and getattr(ctx.fiscal_padrao, "cst_icms", None):
            return ctx.fiscal_padrao.cst_icms
            
        # 2. Decisão por Regime
        is_simples = str(ctx.regime) in ResolverAliquotaPorRegime.REGIME_SIMPLES
        
        if is_simples:
            # TODO: Implementar lógica de CSOSN baseada em CFOP (ex: 5405 -> 500)
            return cls.CSOSN_DEFAULT
        else:
            return cls.CST_ICMS_DEFAULT

    @classmethod
    def resolver_ipi(cls, ctx: FiscalContexto) -> str:
        if ctx.fiscal_padrao and getattr(ctx.fiscal_padrao, "cst_ipi", None):
            return ctx.fiscal_padrao.cst_ipi
            
        # IPI no Simples geralmente não destaca, mas se destacar usa 99 ou 49?
        # Mantendo 50 se tiver alíquota, senão o calculador retorna None
        return cls.CST_IPI_DEFAULT

    @classmethod
    def resolver_pis_cofins(cls, ctx: FiscalContexto) -> str:
        if ctx.fiscal_padrao:
             # Assume que PIS e COFINS usam mesmo CST se um estiver setado
             cst = getattr(ctx.fiscal_padrao, "cst_pis", None) or getattr(ctx.fiscal_padrao, "cst_cofins", None)
             if cst: return cst
        
        is_simples = str(ctx.regime) in ResolverAliquotaPorRegime.REGIME_SIMPLES
        if is_simples:
            return "49" # Outras Operações de Saída
            
        return cls.CST_PIS_COFINS_DEFAULT


class CalculadoraImpostos(ABC):
    """
    Interface para calculadoras de impostos individuais.
    Garante que cada imposto tenha sua própria lógica isolada.
    """
    @abstractmethod
    def calcular_impostos(self, ctx: FiscalContexto, base: Decimal) -> Dict[str, Any]:
        """
        Retorna dicionário com valores calculados:
        {
            "base": Decimal,
            "aliquota": Decimal,
            "valor": Decimal,
            "cst": str (opcional)
        }
        """
        pass
    
    def _d(self, v, casas=2) -> Decimal | None:
        if v is None:
            return None
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        return v.quantize(Decimal(10) ** -casas, ROUND_HALF_UP)

class ResolverBases:
    def resolver(self, ctx: FiscalContexto, base_raiz: Decimal, valor_ipi: Decimal):
        base_icms = base_raiz
        if ctx.cfop and ctx.cfop.cfop_icms_base_inclui_ipi:

            base_icms += valor_ipi

        base_st = base_icms
        if ctx.cfop and ctx.cfop.cfop_st_base_inclui_ipi:
            base_st += valor_ipi

        return BasesFiscal(
            raiz=base_raiz,
            icms=base_icms,
            st=base_st if ctx.cfop and ctx.cfop.cfop_gera_st else None,
            pis_cofins=base_raiz,
            cbs=base_raiz,  # poderá incluir ICMS futuramente
            ibs=base_raiz,  # poderá variar por UF destino

        )


class IPICalculador(CalculadoraImpostos):
    def calcular_impostos(self, ctx: FiscalContexto, base: Decimal) -> Dict[str, Any]:
        if not ctx.cfop or not ctx.cfop.cfop_exig_ipi:
            return {"base": None, "aliquota": None, "valor": None, "cst": None}
        aliq = ctx.aliquotas_base.get("ipi")        
        # Override do Fiscal Padrão
        if ctx.fiscal_padrao and getattr(ctx.fiscal_padrao, "aliq_ipi", None) is not None:
            aliq = ctx.fiscal_padrao.aliq_ipi
        if aliq is None:
            return {"base": None, "aliquota": None, "valor": None, "cst": None}

        valor = self._d(base * (aliq / Decimal("100")))
        cst = ResolverCST.resolver_ipi(ctx)

        return {
            "base": base,
            "aliquota": aliq,
            "valor": valor,
            "cst": cst
        }

class ICMSCalculador(CalculadoraImpostos):
    def calcular_impostos(self, ctx: FiscalContexto, base: Decimal) -> Dict[str, Any]:
        if not ctx.cfop or not ctx.cfop.cfop_exig_icms:
            return {"base": None, "aliquota": None, "valor": None, "cst": None, "st": None}

        # Dados base do ICMS (origem x destino)
        aliq_icms = ctx.icms_data.get("icms")
        
        # Override do Fiscal Padrão
        if ctx.fiscal_padrao and getattr(ctx.fiscal_padrao, "aliq_icms", None) is not None:
            aliq_icms = ctx.fiscal_padrao.aliq_icms

        if aliq_icms is None:
             return {"base": None, "aliquota": None, "valor": None, "cst": None, "st": None}

        valor_icms = self._d(base * (aliq_icms / Decimal("100")))
        # CST Logic
        cst = ResolverCST.resolver_icms(ctx)

        return {
            "base": base,
            "aliquota": aliq_icms,
            "valor": valor_icms,
            "cst": cst,
        }

class IcmsStCalculador:
    def calcular(self, ctx, bases: BasesFiscal, icms_res: Dict) -> Dict:
        if base_st is None:
            return {"base": None, "aliquota": None, "valor": None, "cst": None}

        mva = ctx.icms_data.get("mva_st")
        aliq = ctx.icms_data.get("st_aliq")

        if not mva or not aliq:
            return {"base": None, "aliquota": None, "valor": None, "cst": None}

        base_mva = base_st * (1 + mva / Decimal("100"))
        valor_total = base_mva * (aliq / Decimal("100"))
        valor_st = valor_total - valor_icms


        return {
            "base": base_mva,
            "aliquota": aliq,
            "valor": self._d(valor_st),
            "cst": "10"
        }



class PISCOFINSCalculador(CalculadoraImpostos):
    def calcular_impostos(self, ctx: FiscalContexto, base: Decimal) -> Dict[str, Any]:
        if not ctx.cfop or not ctx.cfop.cfop_exig_pis_cofins:
            return {
                "pis": {"base": None, "aliquota": None, "valor": None, "cst": None},
                "cofins": {"base": None, "aliquota": None, "valor": None, "cst": None}
            }

        aliq_pis = ctx.aliquotas_base.get("pis")
        aliq_cofins = ctx.aliquotas_base.get("cofins")
        
        # Overrides
        if ctx.fiscal_padrao:
            if getattr(ctx.fiscal_padrao, "aliq_pis", None) is not None:
                aliq_pis = ctx.fiscal_padrao.aliq_pis
            if getattr(ctx.fiscal_padrao, "aliq_cofins", None) is not None:
                aliq_cofins = ctx.fiscal_padrao.aliq_cofins

        # CSTs
        cst_pis = ResolverCST.resolver_pis_cofins(ctx)
        cst_cofins = cst_pis # Assume simetria por enquanto

        val_pis = self._d(base * (aliq_pis / Decimal("100"))) if aliq_pis else None
        val_cofins = self._d(base * (aliq_cofins / Decimal("100"))) if aliq_cofins else None

        return {
            "pis": {"base": base, "aliquota": aliq_pis, "valor": val_pis, "cst": cst_pis},
            "cofins": {"base": base, "aliquota": aliq_cofins, "valor": val_cofins, "cst": cst_cofins}
        }

class IBSCBSCalculador(CalculadoraImpostos):
    def calcular_impostos(self, ctx: FiscalContexto, base: Decimal) -> Dict[str, Any]:
        # CBS
        cbs_data = {"base": None, "aliquota": None, "valor": None, "cst": None}
        
        # Calcula se CFOP exige OU se houver override explícito (simulação)
        has_override_cbs = ctx.fiscal_padrao and getattr(ctx.fiscal_padrao, "aliq_cbs", None) is not None
        exige_cbs = ctx.cfop and ctx.cfop.cfop_exig_cbs

        if exige_cbs or has_override_cbs:
            aliq = ctx.aliquotas_base.get("cbs")
            if has_override_cbs:
                aliq = ctx.fiscal_padrao.aliq_cbs
            
            val = self._d(base * (aliq / Decimal("100"))) if aliq is not None else None
            cst = getattr(ctx.fiscal_padrao, "cst_cbs", None) or "01"
            cbs_data = {"base": base, "aliquota": aliq, "valor": val, "cst": cst}

        # IBS
        ibs_data = {"base": None, "aliquota": None, "valor": None, "cst": None}
        
        # Calcula se CFOP exige OU se houver override explícito (simulação)
        has_override_ibs = ctx.fiscal_padrao and getattr(ctx.fiscal_padrao, "aliq_ibs", None) is not None
        exige_ibs = ctx.cfop and ctx.cfop.cfop_exig_ibs

        if exige_ibs or has_override_ibs:
            aliq = ctx.aliquotas_base.get("ibs")
            if has_override_ibs:
                aliq = ctx.fiscal_padrao.aliq_ibs
            
            val = self._d(base * (aliq / Decimal("100"))) if aliq is not None else None
            cst = getattr(ctx.fiscal_padrao, "cst_ibs", None) or "01"
            ibs_data = {"base": base, "aliquota": aliq, "valor": val, "cst": cst}

        return {"cbs": cbs_data, "ibs": ibs_data}


class MotorFiscal:
    """
    Orquestrador Fiscal Determinístico.
    Segregação de responsabilidades:
    1. Resolução de Regras (Contexto)
    2. Definição de Bases
    3. Cálculo de Tributos (Calculators)
    """

    def __init__(self, banco=None):
        self.banco = banco
        self.ipi_calc = IPICalculador()
        self.icms_calc = ICMSCalculador()
        self.icms_st_calc = IcmsStCalculador()
        self.piscofins_calc = PISCOFINSCalculador()
        self.ibscbs_calc = IBSCBSCalculador()

    def _d(self, v, casas=2):
        if v is None: return None
        if not isinstance(v, Decimal): v = Decimal(str(v))
        return v.quantize(Decimal(10) ** -casas, ROUND_HALF_UP)
    
    # -----------------------------
    # DATA FETCHING HELPERS
    # -----------------------------
    def resolver_cfop(self, tipo_oper, uf_origem, uf_destino):
        qs = MapaCFOP.objects
        if self.banco: qs = qs.using(self.banco)
        try:
            mapa = qs.select_related("cfop").get(
                tipo_oper=tipo_oper,
                uf_origem=uf_origem,
                uf_destino=uf_destino,
            )
            return mapa.cfop
        except MapaCFOP.DoesNotExist:
            # Fallback for VENDA operations if specific mapping not found
            if tipo_oper == "VENDA":
                qs_cfop = CFOP.objects
                if self.banco: qs_cfop = qs_cfop.using(self.banco)
                
                if uf_origem == uf_destino:
                    return qs_cfop.filter(cfop_codi="5102").first()
                else:
                    return qs_cfop.filter(cfop_codi="6102").first()
            return None

    def obter_ncm(self, produto):
        if not produto.prod_ncm: return None
        qs = Ncm.objects
        if self.banco: qs = qs.using(self.banco)
        return qs.filter(ncm_codi=produto.prod_ncm).first()

    def obter_icms_data(self, uf_origem, uf_destino):
        qs = TabelaICMS.objects
        if self.banco: qs = qs.using(self.banco)
        tab = qs.filter(uf_origem=uf_origem, uf_destino=uf_destino).first()
        
        if not tab: return {"icms": None, "mva_st": None, "st_aliq": None}
        
        mesma = uf_origem == uf_destino
        return {
            "icms": self._d(tab.aliq_interna if mesma else tab.aliq_inter),
            "mva_st": self._d(tab.mva_st),
            "st_aliq": None 
        }
        
    def obter_aliquotas_base(self, ncm, regime=None):
        return ResolverAliquotaPorRegime().resolver(
            getattr(ncm, 'ncmaliquota', None) if ncm else None, 
            regime
        )

    def resolver_fiscal_padrao(self, produto, ncm, cfop):
        # Prioridade: Produto > NCM > CFOP
        if hasattr(produto, "fiscal") and produto.fiscal: return produto.fiscal
        if hasattr(ncm, "fiscal") and ncm.fiscal: return ncm.fiscal
        if hasattr(cfop, "fiscal") and cfop.fiscal: return cfop.fiscal
        return None

    def aplicar_overrides_dif(self, ncm, cfop, aliquotas, icms_data):
        """Aplica NCM_CFOP_DIF se existir"""
        if not ncm or not cfop: return aliquotas, icms_data
        
        qs = NCM_CFOP_DIF.objects
        if self.banco: qs = qs.using(self.banco)
        try:
            dif = qs.get(ncm=ncm, cfop=cfop)
            
            # Atualiza aliquotas (copia para não mutar o original se for ref)
            new_aliq = aliquotas.copy()
            if dif.ncm_ipi_dif is not None: new_aliq["ipi"] = self._d(dif.ncm_ipi_dif)
            if dif.ncm_pis_dif is not None: new_aliq["pis"] = self._d(dif.ncm_pis_dif)
            if dif.ncm_cofins_dif is not None: new_aliq["cofins"] = self._d(dif.ncm_cofins_dif)
            if dif.ncm_cbs_dif is not None: new_aliq["cbs"] = self._d(dif.ncm_cbs_dif)
            if dif.ncm_ibs_dif is not None: new_aliq["ibs"] = self._d(dif.ncm_ibs_dif)
            
            new_icms = icms_data.copy()
            if dif.ncm_icms_aliq_dif is not None: new_icms["icms"] = self._d(dif.ncm_icms_aliq_dif)
            if dif.ncm_st_aliq_dif is not None: new_icms["st_aliq"] = self._d(dif.ncm_st_aliq_dif)
            
            return new_aliq, new_icms
        except NCM_CFOP_DIF.DoesNotExist:
            return aliquotas, icms_data

    # -----------------------------
    # MAIN CALCULATION
    # -----------------------------
    def calcular_item(self, ctx: FiscalContexto, item, tipo_oper, base_manual: Decimal = None) -> Dict[str, Any]:
        """
        Calcula impostos para um item.
        Popula o contexto se necessário.
        """
        # 1. Resolver Entidades Fiscais
        cfop = ctx.cfop or self.resolver_cfop(tipo_oper, ctx.uf_origem, ctx.uf_destino)
        ncm = ctx.ncm or self.obter_ncm(ctx.produto)

        aliquotas = self.obter_aliquotas_base(ncm, ctx.regime)
        icms_data = self.obter_icms_data(ctx.uf_origem, ctx.uf_destino)

        aliquotas, icms_data = self.aplicar_overrides_dif(
            ncm, cfop, aliquotas, icms_data
        )

        fiscal_padrao = self.resolver_fiscal_padrao(ctx.produto, ncm, cfop)

        ctx_item = replace(
            ctx,
            cfop=cfop,
            ncm=ncm,
            fiscal_padrao=fiscal_padrao,
            aliquotas_base=aliquotas,
            icms_data=icms_data,
        )


        # 5. Calcular Bases
        if base_manual is not None:
            base_raiz = self._d(base_manual)
        elif hasattr(item, "iped_quan"):
            base_raiz = self._d(item.iped_quan * item.iped_unit) # Assumindo campos do item
        else:
            base_raiz = Decimal("0")
        
        # IPI (Calculado antes pois pode compor base ICMS)
        ipi_res = self.ipi_calc.calcular_impostos(ctx_item, base_raiz)
        valor_ipi = ipi_res["valor"] or Decimal("0")

        bases = ResolverBases().resolver(
            ctx=ctx_item,
            base_raiz=base_raiz,
            valor_ipi=valor_ipi
        )

        
        # ICMS + ST
        icms_res = self.icms_calc.calcular_impostos(ctx_item, bases.icms)
        
        # Se houver ST e base ST incluir IPI
        st_res = None
        if ctx_item.cfop and ctx_item.cfop.cfop_gera_st:
            st_res = self.icms_st_calc.calcular_impostos(
                ctx_item,
                bases.st,
                valor_icms_anterior=icms_res["valor"] or Decimal("0")
            )

        # PIS/COFINS
        piscofins_res = self.piscofins_calc.calcular_impostos(ctx_item, bases.pis_cofins)   
        
        # IBS/CBS
        ibscbs_res = self.ibscbs_calc.calcular_impostos(ctx_item, bases.cbs)


        return {
            "cfop": ctx_item.cfop,  
            "bases": {
                "raiz": base_raiz,
                "icms": bases.icms,
                "st": bases.st,
            },
            "valores": {
                "ipi": ipi_res["valor"],
                "icms": icms_res["valor"],
                "st": st_res["valor"] if st_res else None,
                "pis": piscofins_res["pis"]["valor"],
                "cofins": piscofins_res["cofins"]["valor"],
                "cbs": ibscbs_res["cbs"]["valor"],
                "ibs": ibscbs_res["ibs"]["valor"],
            },
            "aliquotas": {
                "ipi": ipi_res["aliquota"],
                "icms": icms_res["aliquota"],
                "st": st_res["aliquota"] if st_res else None,
                "pis": piscofins_res["pis"]["aliquota"],
                "cofins": piscofins_res["cofins"]["aliquota"],
                "cbs": ibscbs_res["cbs"]["aliquota"],
                "ibs": ibscbs_res["ibs"]["aliquota"],
            },
            "csts": {
                "ipi": ipi_res["cst"],
                "icms": icms_res["cst"],
                "pis": piscofins_res["pis"]["cst"],
                "cofins": piscofins_res["cofins"]["cst"],
                "cbs": ibscbs_res["cbs"]["cst"],
                "ibs": ibscbs_res["ibs"]["cst"],
            }
        }
        
    def aplicar_no_item(self, item, pacote):
        """
        Preenche TODOS os campos fiscais do Itenspedidovenda (ou NotaItem via duck typing)
        usando o pacote fiscal calculado.
        """
        # Bases
        item.iped_base_raiz = pacote["bases"]["raiz"]
        item.iped_base_icms = pacote["bases"]["icms"]
        item.iped_base_st = pacote["bases"]["st"]

        # Alíquotas
        item.iped_pipi = pacote["aliquotas"]["ipi"]
        item.iped_aliq_icms = pacote["aliquotas"]["icms"]
        item.iped_aliq_icms_st = pacote["aliquotas"]["st"]
        item.iped_aliq_pis = pacote["aliquotas"]["pis"]
        item.iped_aliq_cofi = pacote["aliquotas"]["cofins"]

        # Valores
        item.iped_vipi = pacote["valores"]["ipi"]
        item.iped_valo_icms = pacote["valores"]["icms"]
        item.iped_valo_icms_st = pacote["valores"]["st"]
        item.iped_valo_pis = pacote["valores"]["pis"]
        item.iped_valo_cofi = pacote["valores"]["cofins"]

        # CSTs
        if pacote["csts"]["icms"]: item.iped_cst_icms = pacote["csts"]["icms"]
        if pacote["csts"]["pis"]: item.iped_cst_pis = pacote["csts"]["pis"]
        if pacote["csts"]["cofins"]: item.iped_cst_cofi = pacote["csts"]["cofins"]
        
        return item
