from ..models import CFOPFiscalPadrao, NcmFiscalPadrao, ProdutoFiscalPadrao


class FiscalPadraoResolver:

    def __init__(self, banco=None):
        self.banco = banco

    def _qs(self, model):
        qs = model.objects
        if self.banco:
            qs = qs.using(self.banco)
        return qs

    def resolver(self, produto, ncm, cfop):

        if produto:
            try:
                fiscal = getattr(produto, "fiscal", None)
            except Exception:
                fiscal = None

            if fiscal:
                return fiscal, "PRODUTO"

            fiscal = self._qs(
                ProdutoFiscalPadrao
            ).filter(produto_id=produto.pk).first()

            if fiscal:
                return fiscal, "PRODUTO"

        if cfop:
            try:
                fiscal = getattr(cfop, "fiscal", None)
            except Exception:
                fiscal = None

            if fiscal:
                return fiscal, "CFOP"

            fiscal = self._qs(
                CFOPFiscalPadrao
            ).filter(cfop_id=cfop.pk).first()

            if fiscal:
                return fiscal, "CFOP"

        if ncm:
            try:
                fiscal = getattr(ncm, "fiscal", None)
            except Exception:
                fiscal = None

            if fiscal:
                return fiscal, "NCM"

            fiscal = self._qs(
                NcmFiscalPadrao
            ).filter(ncm_id=ncm.pk).first()

            if fiscal:
                return fiscal, "NCM"

        return None, None
