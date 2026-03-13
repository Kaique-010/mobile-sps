class CSTResolver:

    CST_ICMS = "00"
    CSOSN = "101"
    CST_IPI = "50"
    CST_PIS_COFINS = "01"

    @classmethod
    def icms(cls, ctx):

        if getattr(ctx, "fiscal_padrao", None) and getattr(ctx.fiscal_padrao, "cst_icms", None):
            return ctx.fiscal_padrao.cst_icms

        regime = str(getattr(ctx, "regime", ""))
        is_simples = regime in {"1", "2", "4", "SIMPLES", "MEI"}

        if is_simples:
            if ctx.cfop:
                cfop_cod = str(getattr(ctx.cfop, "cfop_codi", ""))
                if cfop_cod.startswith("1202") or cfop_cod.startswith("5202"):
                    return "900"

            if ctx.cfop and ctx.cfop.cfop_gera_st:
                return "500"

            return cls.CSOSN

        else:

            if ctx.cfop and ctx.cfop.cfop_gera_st:
                return "10"

            return cls.CST_ICMS

    @classmethod
    def pis_cofins(cls, ctx):

        if getattr(ctx, "fiscal_padrao", None):
            cst = getattr(ctx.fiscal_padrao, "cst_pis", None) or getattr(ctx.fiscal_padrao, "cst_cofins", None)
            if cst:
                return cst

        if str(getattr(ctx, "regime", "")) in {"1", "2", "4", "SIMPLES", "MEI"}:
            return "49"

        return cls.CST_PIS_COFINS

    @classmethod
    def ipi(cls, ctx):

        if getattr(ctx, "fiscal_padrao", None) and getattr(ctx.fiscal_padrao, "cst_ipi", None):
            return ctx.fiscal_padrao.cst_ipi

        if str(getattr(ctx, "regime", "")) in {"1", "2", "4", "SIMPLES", "MEI"}:
            return "99"

        return cls.CST_IPI
