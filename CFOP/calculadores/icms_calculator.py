from decimal import Decimal
from .base_calculator import BaseCalculator
from ..regras.cst_resolver import CSTResolver


class ICMSCalculator(BaseCalculator):

    def calcular(self, ctx, base):

        if not ctx.cfop or not ctx.cfop.cfop_exig_icms:

            return {
                "base": None,
                "aliquota": None,
                "valor": None,
                "cst": None
            }

        aliq = ctx.icms_data.get("icms")

        if ctx.fiscal_padrao and ctx.fiscal_padrao.aliq_icms is not None:
            aliq = ctx.fiscal_padrao.aliq_icms

        if not aliq:

            return {
                "base": None,
                "aliquota": None,
                "valor": None,
                "cst": None
            }

        valor = self._d(base * aliq / self.D100)

        return {
            "base": base,
            "aliquota": aliq,
            "valor": valor,
            "cst": CSTResolver.icms(ctx)
        }
