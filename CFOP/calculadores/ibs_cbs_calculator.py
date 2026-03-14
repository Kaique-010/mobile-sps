from decimal import Decimal
from .base_calculator import BaseCalculator


class IBSCBSCalculator(BaseCalculator):

    def calcular(self, ctx, base):

        exige_cbs = bool(getattr(ctx, "cfop", None) and getattr(ctx.cfop, "cfop_exig_cbs", False))
        exige_ibs = bool(getattr(ctx, "cfop", None) and getattr(ctx.cfop, "cfop_exig_ibs", False))

        if getattr(ctx, "fiscal_padrao", None):
            if getattr(ctx.fiscal_padrao, "aliq_cbs", None) is not None:
                exige_cbs = True
            if getattr(ctx.fiscal_padrao, "aliq_ibs", None) is not None:
                exige_ibs = True
            if getattr(ctx.fiscal_padrao, "cst_cbs", None):
                exige_cbs = True
            if getattr(ctx.fiscal_padrao, "cst_ibs", None):
                exige_ibs = True

        aliq_cbs = ctx.aliquotas_base.get("cbs") or Decimal("0")
        aliq_ibs = ctx.aliquotas_base.get("ibs") or Decimal("0")

        if getattr(ctx, "fiscal_padrao", None):
            if getattr(ctx.fiscal_padrao, "aliq_cbs", None) is not None:
                aliq_cbs = ctx.fiscal_padrao.aliq_cbs
            if getattr(ctx.fiscal_padrao, "aliq_ibs", None) is not None:
                aliq_ibs = ctx.fiscal_padrao.aliq_ibs

        cst_cbs = getattr(getattr(ctx, "fiscal_padrao", None), "cst_cbs", None) or "01"
        cst_ibs = getattr(getattr(ctx, "fiscal_padrao", None), "cst_ibs", None) or "01"

        cbs = {
            "base": base if exige_cbs else None,
            "aliquota": aliq_cbs if exige_cbs else None,
            "valor": self._d(base * aliq_cbs / self.D100) if exige_cbs and aliq_cbs else Decimal("0") if exige_cbs else None,
            "cst": cst_cbs if exige_cbs else None,
        }

        ibs = {
            "base": base if exige_ibs else None,
            "aliquota": aliq_ibs if exige_ibs else None,
            "valor": self._d(base * aliq_ibs / self.D100) if exige_ibs and aliq_ibs else Decimal("0") if exige_ibs else None,
            "cst": cst_ibs if exige_ibs else None,
        }

        return {
            "cbs": cbs,
            "ibs": ibs
        }
