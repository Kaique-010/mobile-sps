from decimal import Decimal
from ..services.bases import BaseFiscal


class BaseResolver:

    def resolver(self, ctx, base_raiz, valor_ipi):

        base_icms = base_raiz

        if ctx.cfop and ctx.cfop.cfop_icms_base_inclui_ipi:
            base_icms += valor_ipi

        base_st = base_raiz

        if ctx.cfop and ctx.cfop.cfop_st_base_inclui_ipi:
            base_st += valor_ipi

        if not (ctx.cfop and ctx.cfop.cfop_gera_st):
            base_st = None

        return BaseFiscal(
            raiz=base_raiz,
            icms=base_icms,
            st=base_st,
            pis_cofins=base_raiz,
            cbs=base_raiz,
            ibs=base_raiz,
        )