from decimal import Decimal
from .base_calculator import BaseCalculator
from ..regras.cst_resolver import CSTResolver


class PISCOFINSCalculator(BaseCalculator):

    def calcular(self, ctx, base):

        if not ctx.cfop or not ctx.cfop.cfop_exig_pis_cofins:

            return {
                "pis": {"base": None, "aliquota": None, "valor": None, "cst": None},
                "cofins": {"base": None, "aliquota": None, "valor": None, "cst": None},
            }

        aliq_pis = ctx.aliquotas_base.get("pis") or Decimal("0")
        aliq_cofins = ctx.aliquotas_base.get("cofins") or Decimal("0")

        if getattr(ctx, "fiscal_padrao", None):
            if getattr(ctx.fiscal_padrao, "aliq_pis", None) is not None:
                aliq_pis = ctx.fiscal_padrao.aliq_pis
            if getattr(ctx.fiscal_padrao, "aliq_cofins", None) is not None:
                aliq_cofins = ctx.fiscal_padrao.aliq_cofins

        val_pis = self._d(base * aliq_pis / self.D100) if aliq_pis else Decimal("0")
        val_cofins = self._d(base * aliq_cofins / self.D100) if aliq_cofins else Decimal("0")

        cst = CSTResolver.pis_cofins(ctx)

        return {
            "pis": {
                "base": base,
                "aliquota": aliq_pis,
                "valor": val_pis,
                "cst": cst
            },
            "cofins": {
                "base": base,
                "aliquota": aliq_cofins,
                "valor": val_cofins,
                "cst": cst
            }
        }
