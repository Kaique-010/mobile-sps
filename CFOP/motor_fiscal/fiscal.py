from decimal import Decimal, ROUND_HALF_UP
from dataclasses import replace

from ..services.bases import FiscalContexto

from ..auxiliares.cfop_resolver import CFOPResolver
from ..auxiliares.ncm_resolver import NCMResolver
from ..auxiliares.aliquota_resolver import AliquotaResolver
from ..auxiliares.icms_table_resolver import ICMSTableResolver
from ..auxiliares.fiscal_padrao_resolver import FiscalPadraoResolver

from ..bases.base_resolver import BaseResolver

from ..calculadores.ipi_calculator import IPICalculator
from ..calculadores.icms_calculator import ICMSCalculator
from ..calculadores.icms_st_calculator import ICMSSTCalculator
from ..calculadores.pis_cofins_calculator import PISCOFINSCalculator
from ..calculadores.ibs_cbs_calculator import IBSCBSCalculator
from ..models import NCM_CFOP_DIF


class FiscalEngine:

    def __init__(self, banco=None):

        self.banco = banco

        # resolvers
        self.cfop_resolver = CFOPResolver(banco)
        self.ncm_resolver = NCMResolver(banco)
        self.aliquota_resolver = AliquotaResolver()
        self.icms_resolver = ICMSTableResolver(banco)
        self.fiscal_padrao_resolver = FiscalPadraoResolver(banco)

        # bases
        self.base_resolver = BaseResolver()

        # calculadores
        self.ipi_calc = IPICalculator()
        self.icms_calc = ICMSCalculator()
        self.icms_st_calc = ICMSSTCalculator()
        self.piscofins_calc = PISCOFINSCalculator()
        self.ibscbs_calc = IBSCBSCalculator()
    
    def _d(self, v, casas=2):
        if v is None:
            return None
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        return v.quantize(Decimal(10) ** -casas, ROUND_HALF_UP)
    
    def resolver_cfop(self, tipo_oper, uf_origem, uf_destino):
        return self.cfop_resolver.resolver(tipo_oper, uf_origem, uf_destino)
    
    def obter_ncm(self, produto):
        return self.ncm_resolver.resolver(produto)
    
    def obter_aliquotas_base(self, ncm, regime=None):
        return self.aliquota_resolver.resolver(getattr(ncm, "ncmaliquota", None) if ncm else None, regime)
    
    def obter_icms_data(self, uf_origem, uf_destino, empresa_id=None):
        return self.icms_resolver.resolver(uf_origem, uf_destino, empresa_id)
    
    def resolver_fiscal_padrao(self, produto, ncm, cfop, uf_origem=None, uf_destino=None, tipo_entidade=None):
        return self.fiscal_padrao_resolver.resolver(
            produto,
            ncm,
            cfop,
            uf_origem=uf_origem,
            uf_destino=uf_destino,
            tipo_entidade=tipo_entidade,
        )
    
    def aplicar_overrides_dif(self, ncm, cfop, aliquotas, icms_data):
        if not ncm or not cfop:
            return aliquotas, icms_data
        
        qs = NCM_CFOP_DIF.objects
        if self.banco:
            qs = qs.using(self.banco)
        dif = qs.filter(ncm=ncm, cfop=cfop).first()
        if not dif:
            return aliquotas, icms_data
        
        new_aliq = dict(aliquotas or {})
        if dif.ncm_ipi_dif is not None:
            new_aliq["ipi"] = self._d(dif.ncm_ipi_dif)
        if dif.ncm_pis_dif is not None:
            new_aliq["pis"] = self._d(dif.ncm_pis_dif)
        if dif.ncm_cofins_dif is not None:
            new_aliq["cofins"] = self._d(dif.ncm_cofins_dif)
        if dif.ncm_cbs_dif is not None:
            new_aliq["cbs"] = self._d(dif.ncm_cbs_dif)
        if dif.ncm_ibs_dif is not None:
            new_aliq["ibs"] = self._d(dif.ncm_ibs_dif)
        
        new_icms = dict(icms_data or {})
        if dif.ncm_icms_aliq_dif is not None:
            new_icms["icms"] = self._d(dif.ncm_icms_aliq_dif)
        if dif.ncm_st_aliq_dif is not None:
            new_icms["st_aliq"] = self._d(dif.ncm_st_aliq_dif)
        
        return new_aliq, new_icms
    
    def aplicar_no_item(self, item, pacote):
        item.iped_base_raiz = pacote["bases"]["raiz"]
        item.iped_base_icms = pacote["bases"]["icms"]
        item.iped_base_st = pacote["bases"]["st"]

        item.iped_pipi = pacote["aliquotas"]["ipi"]
        item.iped_aliq_icms = pacote["aliquotas"]["icms"]
        item.iped_aliq_icms_st = pacote["aliquotas"]["st"]
        item.iped_aliq_pis = pacote["aliquotas"]["pis"]
        item.iped_aliq_cofi = pacote["aliquotas"]["cofins"]

        item.iped_vipi = pacote["valores"]["ipi"]
        item.iped_valo_icms = pacote["valores"]["icms"]
        item.iped_valo_icms_st = pacote["valores"]["st"]
        item.iped_valo_pis = pacote["valores"]["pis"]
        item.iped_valo_cofi = pacote["valores"]["cofins"]

        if pacote["csts"]["icms"]:
            item.iped_cst_icms = pacote["csts"]["icms"]
        if pacote["csts"]["pis"]:
            item.iped_cst_pis = pacote["csts"]["pis"]
        if pacote["csts"]["cofins"]:
            item.iped_cst_cofi = pacote["csts"]["cofins"]
        if pacote["csts"]["ibs"]:
            item.iped_cst_ibs = pacote["csts"]["ibs"]
        if pacote["csts"]["cbs"]:
            item.iped_cst_cbs = pacote["csts"]["cbs"]

        return item
    
    def calcular_item(self, ctx: FiscalContexto, item, tipo_oper, base_manual: Decimal = None):
        """
        Calcula os impostos de um item com base no contexto fiscal.
        """
        cfop = ctx.cfop or self.resolver_cfop(tipo_oper, ctx.uf_origem, ctx.uf_destino)
        ncm = ctx.ncm or self.obter_ncm(ctx.produto)

        aliquotas = self.obter_aliquotas_base(ncm, ctx.regime)
        icms_data = self.obter_icms_data(ctx.uf_origem, ctx.uf_destino, ctx.empresa_id)

        aliquotas, icms_data = self.aplicar_overrides_dif(ncm, cfop, aliquotas, icms_data)

        fiscal_padrao, fonte = self.resolver_fiscal_padrao(
            ctx.produto,
            ncm,
            cfop,
            uf_origem=ctx.uf_origem,
            uf_destino=ctx.uf_destino,
            tipo_entidade=getattr(ctx, "tipo_entidade", None),
        )
        if not fonte:
            if ncm:
                fonte = "NCM"
            elif cfop:
                fonte = "CFOP"
            else:
                fonte = "Padrão"
        
        ctx = replace(
            ctx,
            cfop=cfop,
            ncm=ncm,
            fiscal_padrao=fiscal_padrao,
            aliquotas_base=aliquotas,
            icms_data=icms_data,
        )
        
        if base_manual is not None:
            base_raiz = self._d(base_manual)
        elif item is not None and hasattr(item, "quantidade"):
            base_raiz = self._d(item.quantidade * item.unitario - (item.desconto or Decimal("0")))
        else:
            base_raiz = Decimal("0")
        
        ipi_res = self.ipi_calc.calcular(ctx, base_raiz)

        valor_ipi = ipi_res["valor"] or Decimal("0")
        bases = self.base_resolver.resolver(
            ctx,
            base_raiz,
            valor_ipi,
        )
        icms_res = self.icms_calc.calcular(
            ctx,
            bases.icms,
        )
        st_res = {"base": None, "aliquota": None, "valor": None, "cst": None}

        if ctx.cfop and ctx.cfop.cfop_gera_st and bases.st:

            st_res = self.icms_st_calc.calcular(
                ctx,
                bases.st,
                icms_res["valor"]
            )
            
        piscofins_res = self.piscofins_calc.calcular(
            ctx,
            bases.pis_cofins,
        )
        
        ibscbs_res = self.ibscbs_calc.calcular(
            ctx,
            bases.cbs,
        )
        return {

        "cfop": ctx.cfop,
        "ncm": ctx.ncm,
        "fonte_tributacao": fonte,

        "bases": {
            "raiz": base_raiz,
            "icms": icms_res["base"],
            "st": st_res["base"],
            "ipi": ipi_res["base"],
            "pis": piscofins_res["pis"]["base"],
            "cofins": piscofins_res["cofins"]["base"],
            "cbs": ibscbs_res["cbs"]["base"],
            "ibs": ibscbs_res["ibs"]["base"],
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
        },

        "extras": {
            "mva_st": ctx.icms_data.get("mva_st"),
        }
    }
