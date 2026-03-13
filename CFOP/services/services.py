from ..motor_fiscal.fiscal import FiscalEngine as MotorFiscal
from ..regras.cst_resolver import CSTResolver
from .auxiliares import ResolverAliquotaPorRegime, get_empresa_uf_origem, get_regime
from .bases import BaseFiscal, FiscalContexto


class ResolverCST:
    CST_ICMS_DEFAULT = "00"
    CSOSN_DEFAULT = "101"
    CST_IPI_DEFAULT = "50"
    CST_PIS_COFINS_DEFAULT = "01"

    @classmethod
    def resolver_icms(cls, ctx: FiscalContexto) -> str:
        return CSTResolver.icms(ctx)

    @classmethod
    def resolver_ipi(cls, ctx: FiscalContexto) -> str:
        return CSTResolver.ipi(ctx)

    @classmethod
    def resolver_pis_cofins(cls, ctx: FiscalContexto) -> str:
        return CSTResolver.pis_cofins(ctx)
