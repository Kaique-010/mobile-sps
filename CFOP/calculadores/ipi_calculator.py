from decimal import Decimal
from .base_calculator import BaseCalculator
from ..regras.cst_resolver import CSTResolver


class IPICalculator(BaseCalculator):

    def calcular(self, ctx, base):

        if not ctx.cfop or not ctx.cfop.cfop_exig_ipi:

            return {
                "base": None,
                "aliquota": None,
                "valor": None,
                "cst": None
            }

        aliq = ctx.aliquotas_base.get("ipi")

        if ctx.fiscal_padrao and ctx.fiscal_padrao.aliq_ipi is not None:
            aliq = ctx.fiscal_padrao.aliq_ipi

        if not aliq:

            return {
                "base": base,
                "aliquota": Decimal("0"),
                "valor": Decimal("0"),
                "cst": CSTResolver.ipi(ctx)
            }

        valor = self._d(base * aliq / self.D100)

        return {
            "base": base,
            "aliquota": aliq,
            "valor": valor,
            "cst": CSTResolver.ipi(ctx)
        }
