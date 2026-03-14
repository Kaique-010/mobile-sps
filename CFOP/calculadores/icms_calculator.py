from decimal import Decimal
from .base_calculator import BaseCalculator
from ..regras.cst_resolver import CSTResolver


class ICMSCalculator(BaseCalculator):

    def calcular(self, ctx, base):

        exige_icms = bool(ctx.cfop and getattr(ctx.cfop, "cfop_exig_icms", False))
        exige_por_padrao = False
        if getattr(ctx, "fiscal_padrao", None):
            if getattr(ctx.fiscal_padrao, "aliq_icms", None) is not None:
                exige_por_padrao = True
            if getattr(ctx.fiscal_padrao, "cst_icms", None):
                exige_por_padrao = True
        if exige_por_padrao:
            exige_icms = True

        if not exige_icms:

            return {
                "base": None,
                "aliquota": None,
                "valor": None,
                "cst": None
            }

        aliq = ctx.icms_data.get("icms")

        if ctx.fiscal_padrao and ctx.fiscal_padrao.aliq_icms is not None:
            aliq = ctx.fiscal_padrao.aliq_icms

        if aliq is None:
            if exige_por_padrao:
                aliq = Decimal("0")
            else:
                return {
                    "base": None,
                    "aliquota": None,
                    "valor": None,
                    "cst": None
                }

        valor = self._d(base * aliq / self.D100) if aliq else Decimal("0")

        return {
            "base": base,
            "aliquota": aliq,
            "valor": valor,
            "cst": CSTResolver.icms(ctx)
        }
