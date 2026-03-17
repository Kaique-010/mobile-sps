from ..models import CFOPFiscalPadrao, NcmFiscalPadrao, ProdutoFiscalPadrao


class FiscalPadraoResolver:

    def __init__(self, banco=None):
        self.banco = banco

    def _qs(self, model):
        qs = model.objects
        if self.banco:
            qs = qs.using(self.banco)
        return qs
    
    def _match_contexto(self, fiscal, uf_origem=None, uf_destino=None, tipo_entidade=None, cfop=None):
        if not fiscal:
            return False

        def _norm_upper(v):
            return v.strip().upper() if isinstance(v, str) else ""

        fiscal_uf_origem = _norm_upper(getattr(fiscal, "uf_origem", None))
        fiscal_uf_destino = _norm_upper(getattr(fiscal, "uf_destino", None))
        fiscal_tipo_entidade = _norm_upper(getattr(fiscal, "tipo_entidade", None))
        fiscal_cfop = getattr(fiscal, "cfop", None)

        ctx_uf_origem = _norm_upper(uf_origem)
        ctx_uf_destino = _norm_upper(uf_destino)
        ctx_tipo_entidade = _norm_upper(tipo_entidade)
        ctx_cfop = getattr(cfop, "cfop_codi", None)
        ctx_cfop = ctx_cfop.strip() if isinstance(ctx_cfop, str) else ""

        if isinstance(fiscal_cfop, str):
            fiscal_cfop = fiscal_cfop.strip()
            if fiscal_cfop:
                if ctx_cfop and fiscal_cfop != ctx_cfop:
                    return False

        if fiscal_uf_origem:
            if not ctx_uf_origem or fiscal_uf_origem != ctx_uf_origem:
                return False

        if fiscal_uf_destino:
            if not ctx_uf_destino or fiscal_uf_destino != ctx_uf_destino:
                return False

        if fiscal_tipo_entidade:
            if not ctx_tipo_entidade:
                return False
            if ctx_tipo_entidade == "AM":
                return True
            if fiscal_tipo_entidade == "AM":
                return True
            if fiscal_tipo_entidade != ctx_tipo_entidade:
                return False

        return True
    
    def _pick_best(self, fiscals, uf_origem=None, uf_destino=None, tipo_entidade=None, cfop=None):
        best = None
        best_score = -1
        for fiscal in fiscals:
            if not self._match_contexto(fiscal, uf_origem=uf_origem, uf_destino=uf_destino, tipo_entidade=tipo_entidade, cfop=cfop):
                continue
            score = 0
            if (getattr(fiscal, "uf_origem", None) or "").strip():
                score += 1
            if (getattr(fiscal, "uf_destino", None) or "").strip():
                score += 1
            if (getattr(fiscal, "tipo_entidade", None) or "").strip():
                score += 1
            if isinstance(getattr(fiscal, "cfop", None), str) and (getattr(fiscal, "cfop", None) or "").strip():
                score += 1
            if score > best_score:
                best = fiscal
                best_score = score
        return best

    def resolver(self, produto, ncm, cfop, uf_origem=None, uf_destino=None, tipo_entidade=None):

        if produto:
            try:
                fiscal = getattr(produto, "fiscal", None)
            except Exception:
                fiscal = None

            if fiscal and self._match_contexto(fiscal, uf_origem=uf_origem, uf_destino=uf_destino, tipo_entidade=tipo_entidade, cfop=cfop):
                return fiscal, "PRODUTO"

            fiscal = self._qs(
                ProdutoFiscalPadrao
            ).filter(produto_id=produto.pk).first()

            if fiscal and self._match_contexto(fiscal, uf_origem=uf_origem, uf_destino=uf_destino, tipo_entidade=tipo_entidade, cfop=cfop):
                return fiscal, "PRODUTO"

        if cfop:
            try:
                fiscal = getattr(cfop, "fiscal", None)
            except Exception:
                fiscal = None

            if fiscal and self._match_contexto(fiscal, uf_origem=uf_origem, uf_destino=uf_destino, tipo_entidade=tipo_entidade, cfop=cfop):
                return fiscal, "CFOP"

            fiscal = self._qs(
                CFOPFiscalPadrao
            ).filter(cfop_id=cfop.pk).first()

            if fiscal and self._match_contexto(fiscal, uf_origem=uf_origem, uf_destino=uf_destino, tipo_entidade=tipo_entidade, cfop=cfop):
                return fiscal, "CFOP"

        if ncm:
            fiscals = self._qs(NcmFiscalPadrao).filter(ncm_id=ncm.pk)
            fiscal = self._pick_best(fiscals, uf_origem=uf_origem, uf_destino=uf_destino, tipo_entidade=tipo_entidade, cfop=cfop)
            if fiscal:
                return fiscal, "NCM"

        return None, None
