from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_HALF_UP
import logging
from django.core.exceptions import ObjectDoesNotExist
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
    CST_IPI_DEFAULT = "50"
    CST_PIS_COFINS_DEFAULT = "01"
    
    @classmethod
    def resolver_icms(cls, ctx: FiscalContexto) -> str:
        # 1. Override explícito do cadastro
        if ctx.fiscal_padrao and getattr(ctx.fiscal_padrao, "cst_icms", None):
            return ctx.fiscal_padrao.cst_icms
            
        # 2. Decisão por Regime
        is_simples = str(ctx.regime) in ResolverAliquotaPorRegime.REGIME_SIMPLES
        
        if is_simples:
            # Regras CSOSN baseadas no CFOP
            if ctx.cfop:
                cfop_cod = str(ctx.cfop.cfop_codi)
                # Devolução → 900
                if cfop_cod.startswith("1202") or cfop_cod.startswith("5202"):
                    return "900"
                # ST → 500
                if ctx.cfop.cfop_gera_st:
                    return "500"
            return cls.CSOSN_DEFAULT
        else:
            # Regime Normal: se tem ST → 10, senão → 00
            if ctx.cfop and ctx.cfop.cfop_gera_st:
                return "10"
            return cls.CST_ICMS_DEFAULT

    @classmethod
    def resolver_ipi(cls, ctx: FiscalContexto) -> str:
        if ctx.fiscal_padrao and getattr(ctx.fiscal_padrao, "cst_ipi", None):
            return ctx.fiscal_padrao.cst_ipi
        
        # Simples: 99 (Outras Saídas)
        is_simples = str(ctx.regime) in ResolverAliquotaPorRegime.REGIME_SIMPLES
        if is_simples:
            return "99"
            
        return cls.CST_IPI_DEFAULT

    @classmethod
    def resolver_pis_cofins(cls, ctx: FiscalContexto) -> str:
        if ctx.fiscal_padrao:
            cst = getattr(ctx.fiscal_padrao, "cst_pis", None) or getattr(ctx.fiscal_padrao, "cst_cofins", None)
            if cst: return cst
        
        is_simples = str(ctx.regime) in ResolverAliquotaPorRegime.REGIME_SIMPLES
        if is_simples:
            return "49"
            
        return cls.CST_PIS_COFINS_DEFAULT


class CalculadoraImpostos(ABC):
    """Interface para calculadoras de impostos individuais."""
    
    @abstractmethod
    def calcular_impostos(self, ctx: FiscalContexto, base: Decimal) -> Dict[str, Any]:
        pass
    
    def _d(self, v, casas=2) -> Decimal | None:
        if v is None:
            return None
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        return v.quantize(Decimal(10) ** -casas, ROUND_HALF_UP)


class ResolverBases:
    """
    Resolve as bases de cálculo conforme regras fiscais:
    - Base ICMS pode incluir IPI (Art. 13, §1º, II, "a" da LC 87/96)
    - Base ST pode incluir IPI + MVA
    """
    def resolver(self, ctx: FiscalContexto, base_raiz: Decimal, valor_ipi: Decimal):
        base_icms = base_raiz
        
        # ICMS inclui IPI se configurado no CFOP
        if ctx.cfop and ctx.cfop.cfop_icms_base_inclui_ipi and valor_ipi:
            base_icms += valor_ipi

        # Base ST = Base ICMS (que já pode ter IPI incluído)
        base_st = base_icms
        
        # Se não gera ST, não há base ST
        if not (ctx.cfop and ctx.cfop.cfop_gera_st):
            base_st = None

        return BasesFiscal(
            raiz=base_raiz,
            icms=base_icms,
            st=base_st,
            pis_cofins=base_raiz,
            cbs=base_raiz,
            ibs=base_raiz,
        )


class IPICalculador(CalculadoraImpostos):
    def calcular_impostos(self, ctx: FiscalContexto, base: Decimal) -> Dict[str, Any]:
        if not ctx.cfop or not ctx.cfop.cfop_exig_ipi:
            return {"base": None, "aliquota": None, "valor": None, "cst": None}
        
        aliq = ctx.aliquotas_base.get("ipi")
        
        # Override do Fiscal Padrão
        if ctx.fiscal_padrao and getattr(ctx.fiscal_padrao, "aliq_ipi", None) is not None:
            aliq = ctx.fiscal_padrao.aliq_ipi
        
        if aliq is None or aliq == 0:
            cst = ResolverCST.resolver_ipi(ctx)
            return {"base": base, "aliquota": Decimal("0"), "valor": Decimal("0"), "cst": cst}

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
            return {"base": None, "aliquota": None, "valor": None, "cst": None}

        aliq_icms = ctx.icms_data.get("icms")
        
        # Override do Fiscal Padrão
        if ctx.fiscal_padrao and getattr(ctx.fiscal_padrao, "aliq_icms", None) is not None:
            aliq_icms = ctx.fiscal_padrao.aliq_icms

        if aliq_icms is None:
            return {"base": None, "aliquota": None, "valor": None, "cst": None}

        valor_icms = self._d(base * (aliq_icms / Decimal("100")))
        cst = ResolverCST.resolver_icms(ctx)

        return {
            "base": base,
            "aliquota": aliq_icms,
            "valor": valor_icms,
            "cst": cst,
        }


class IcmsStCalculador(CalculadoraImpostos):
    """
    Calcula ICMS ST conforme:
    - Base ST = Base ICMS × (1 + MVA)
    - ICMS ST = (Base ST × Alíq ST) - ICMS Próprio
    """
    def calcular_impostos(self, ctx: FiscalContexto, base: Decimal, valor_icms_proprio: Decimal = None) -> Dict[str, Any]:
        # ✅ CORREÇÃO: usar bases.st corretamente
        if base is None:
            return {"base": None, "aliquota": None, "valor": None, "cst": None}

        mva = ctx.icms_data.get("mva_st")
        aliq_st = ctx.icms_data.get("st_aliq")
        
        # Se não tem alíquota ST, busca a interestadual da tabela
        if not aliq_st:
            aliq_st = ctx.icms_data.get("icms")

        if not mva or not aliq_st:
            return {"base": None, "aliquota": None, "valor": None, "cst": None}

        # Base ST = Base ICMS × (1 + MVA/100)
        base_st_calc = base * (Decimal("1") + mva / Decimal("100"))
        
        # ICMS ST total = Base ST × Alíquota ST
        icms_st_total = base_st_calc * (aliq_st / Decimal("100"))
        
        # ICMS ST devido = ICMS ST total - ICMS Próprio
        valor_icms_prop = valor_icms_proprio or Decimal("0")
        icms_st_devido = icms_st_total - valor_icms_prop

        # CST para ST
        is_simples = str(ctx.regime) in ResolverAliquotaPorRegime.REGIME_SIMPLES
        cst = "500" if is_simples else "10"

        return {
            "base": self._d(base_st_calc),
            "aliquota": aliq_st,
            "valor": self._d(icms_st_devido),
            "cst": cst
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

        cst_pis = ResolverCST.resolver_pis_cofins(ctx)
        cst_cofins = cst_pis

        val_pis = self._d(base * (aliq_pis / Decimal("100"))) if aliq_pis else Decimal("0")
        val_cofins = self._d(base * (aliq_cofins / Decimal("100"))) if aliq_cofins else Decimal("0")

        return {
            "pis": {"base": base, "aliquota": aliq_pis or Decimal("0"), "valor": val_pis, "cst": cst_pis},
            "cofins": {"base": base, "aliquota": aliq_cofins or Decimal("0"), "valor": val_cofins, "cst": cst_cofins}
        }


class IBSCBSCalculador(CalculadoraImpostos):
    def calcular_impostos(self, ctx: FiscalContexto, base: Decimal) -> Dict[str, Any]:
        # CBS
        cbs_data = {"base": None, "aliquota": None, "valor": None, "cst": None}
        
        has_override_cbs = ctx.fiscal_padrao and getattr(ctx.fiscal_padrao, "aliq_cbs", None) is not None
        exige_cbs = ctx.cfop and ctx.cfop.cfop_exig_cbs

        if exige_cbs or has_override_cbs:
            aliq = ctx.aliquotas_base.get("cbs") or Decimal("0")
            if has_override_cbs:
                aliq = ctx.fiscal_padrao.aliq_cbs
            
            val = self._d(base * (aliq / Decimal("100"))) if aliq else Decimal("0")
            cst = getattr(ctx.fiscal_padrao, "cst_cbs", None) or "01"
            cbs_data = {"base": base, "aliquota": aliq, "valor": val, "cst": cst}

        # IBS
        ibs_data = {"base": None, "aliquota": None, "valor": None, "cst": None}
        
        has_override_ibs = ctx.fiscal_padrao and getattr(ctx.fiscal_padrao, "aliq_ibs", None) is not None
        exige_ibs = ctx.cfop and ctx.cfop.cfop_exig_ibs

        if exige_ibs or has_override_ibs:
            aliq = ctx.aliquotas_base.get("ibs") or Decimal("0")
            if has_override_ibs:
                aliq = ctx.fiscal_padrao.aliq_ibs
            
            val = self._d(base * (aliq / Decimal("100"))) if aliq else Decimal("0")
            cst = getattr(ctx.fiscal_padrao, "cst_ibs", None) or "01"
            ibs_data = {"base": base, "aliquota": aliq, "valor": val, "cst": cst}

        return {"cbs": cbs_data, "ibs": ibs_data}


class MotorFiscal:
    """Orquestrador Fiscal Determinístico."""

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
        
        cod = str(produto.prod_ncm).strip()
        ncm = qs.filter(ncm_codi=cod).first()
        
        if not ncm and ('.' in cod):
            cod_clean = cod.replace('.', '')
            ncm = qs.filter(ncm_codi=cod_clean).first()
             
        return ncm

    def obter_icms_data(self, uf_origem, uf_destino):
        qs = TabelaICMS.objects
        if self.banco: qs = qs.using(self.banco)
        tab = qs.filter(uf_origem=uf_origem, uf_destino=uf_destino).first()
        
        if not tab: return {"icms": None, "mva_st": None, "st_aliq": None}
        
        mesma = uf_origem == uf_destino
        return {
            "icms": self._d(tab.aliq_interna if mesma else tab.aliq_inter),
            "mva_st": self._d(tab.mva_st),
            "st_aliq": self._d(tab.aliq_interna) if mesma else self._d(tab.aliq_inter)
        }
        
    def obter_aliquotas_base(self, ncm, regime=None):
        return ResolverAliquotaPorRegime().resolver(
            getattr(ncm, 'ncmaliquota', None) if ncm else None, 
            regime
        )

    def resolver_fiscal_padrao(self, produto, ncm, cfop):
        if produto is not None:
            try:
                if produto.fiscal:
                    return produto.fiscal, "PRODUTO"
            except ObjectDoesNotExist:
                pass

        if cfop is not None:
            try:
                if cfop.fiscal:
                    return cfop.fiscal, "CFOP"
            except ObjectDoesNotExist:
                pass

        if ncm is not None:
            try:
                if ncm.fiscal:
                    return ncm.fiscal, "NCM"
            except ObjectDoesNotExist:
                pass

        return None, None

    def aplicar_overrides_dif(self, ncm, cfop, aliquotas, icms_data):
        if not ncm or not cfop: return aliquotas, icms_data
        
        qs = NCM_CFOP_DIF.objects
        if self.banco: qs = qs.using(self.banco)
        try:
            dif = qs.get(ncm=ncm, cfop=cfop)
            
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

    def calcular_item(self, ctx: FiscalContexto, item, tipo_oper, base_manual: Decimal = None) -> Dict[str, Any]:
        # 1. Resolver Entidades Fiscais
        cfop = ctx.cfop or self.resolver_cfop(tipo_oper, ctx.uf_origem, ctx.uf_destino)
        ncm = ctx.ncm or self.obter_ncm(ctx.produto)

        aliquotas = self.obter_aliquotas_base(ncm, ctx.regime)
        icms_data = self.obter_icms_data(ctx.uf_origem, ctx.uf_destino)

        aliquotas, icms_data = self.aplicar_overrides_dif(
            ncm, cfop, aliquotas, icms_data
        )

        fiscal_padrao, fonte_fiscal = self.resolver_fiscal_padrao(ctx.produto, ncm, cfop)

        ctx_item = replace(
            ctx,
            cfop=cfop,
            ncm=ncm,
            fiscal_padrao=fiscal_padrao,
            aliquotas_base=aliquotas,
            icms_data=icms_data,
        )

        # 2. Base de Cálculo
        if base_manual is not None:
            base_raiz = self._d(base_manual)
        elif hasattr(item, "quantidade"):
            base_raiz = self._d(item.quantidade * item.unitario - (item.desconto or Decimal("0")))
        else:
            base_raiz = Decimal("0")
        
        # 3. IPI (pode compor base ICMS)
        ipi_res = self.ipi_calc.calcular_impostos(ctx_item, base_raiz)
        valor_ipi = ipi_res["valor"] or Decimal("0")

        # 4. Resolver Bases
        bases = ResolverBases().resolver(
            ctx=ctx_item,
            base_raiz=base_raiz,
            valor_ipi=valor_ipi
        )

        # 5. ICMS
        icms_res = self.icms_calc.calcular_impostos(ctx_item, bases.icms)
        
        # 6. ICMS ST (✅ CORREÇÃO: passar valor do ICMS próprio)
        st_res = {"base": None, "aliquota": None, "valor": None, "cst": None}
        if ctx_item.cfop and ctx_item.cfop.cfop_gera_st and bases.st:
            st_res = self.icms_st_calc.calcular_impostos(
                ctx_item,
                bases.st,
                valor_icms_proprio=icms_res["valor"] or Decimal("0")
            )

        # 7. PIS/COFINS
        piscofins_res = self.piscofins_calc.calcular_impostos(ctx_item, bases.pis_cofins)   
        
        # 8. IBS/CBS
        ibscbs_res = self.ibscbs_calc.calcular_impostos(ctx_item, bases.cbs)

        return {
            "cfop": ctx_item.cfop,
            "ncm": ctx_item.ncm,
            "fonte_tributacao": fonte_fiscal,
            "bases": {
                "raiz": base_raiz,
                "icms": bases.icms,
                "st": bases.st,
            },
            "valores": {
                "ipi": ipi_res["valor"],
                "icms": icms_res["valor"],
                "st": st_res["valor"],
                "pis": piscofins_res["pis"]["valor"],
                "cofins": piscofins_res["cofins"]["valor"],
                "cbs": ibscbs_res["cbs"]["valor"],
                "ibs": ibscbs_res["ibs"]["valor"],
            },
            "aliquotas": {
                "ipi": ipi_res["aliquota"],
                "icms": icms_res["aliquota"],
                "st": st_res["aliquota"],
                "pis": piscofins_res["pis"]["aliquota"],
                "cofins": piscofins_res["cofins"]["aliquota"],
                "cbs": ibscbs_res["cbs"]["aliquota"],
                "ibs": ibscbs_res["ibs"]["aliquota"],
            },
            "csts": {
                "ipi": ipi_res["cst"],
                "icms": icms_res["cst"],
                "st": st_res.get("cst"),
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
