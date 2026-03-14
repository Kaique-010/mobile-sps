from decimal import Decimal
from .base_calculator import BaseCalculator
from ..regras.cst_resolver import CSTResolver


class IPICalculator(BaseCalculator):

    def calcular(self, ctx, base):

        exige_ipi = bool(ctx.cfop and getattr(ctx.cfop, "cfop_exig_ipi", False))
        if getattr(ctx, "fiscal_padrao", None):
            if getattr(ctx.fiscal_padrao, "aliq_ipi", None) is not None:
                exige_ipi = True
            if getattr(ctx.fiscal_padrao, "cst_ipi", None):
                exige_ipi = True

        if not exige_ipi:

            return {
                "base": None,
                "aliquota": None,
                "valor": None,
                "cst": None
            }

        aliq = ctx.aliquotas_base.get("ipi")

        if ctx.fiscal_padrao and ctx.fiscal_padrao.aliq_ipi is not None:
            aliq = ctx.fiscal_padrao.aliq_ipi

        if aliq is None:

            return {
                "base": base,
                "aliquota": Decimal("0"),
                "valor": Decimal("0"),
                "cst": CSTResolver.ipi(ctx)
            }

        valor = self._d(base * aliq / self.D100) if aliq else Decimal("0")

        return {
            "base": base,
            "aliquota": aliq,
            "valor": valor,
            "cst": CSTResolver.ipi(ctx)
        }
