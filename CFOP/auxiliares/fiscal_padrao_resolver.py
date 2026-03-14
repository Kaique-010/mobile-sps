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
        
        fiscal_uf_origem = (getattr(fiscal, "uf_origem", None) or "").strip().upper()
        fiscal_uf_destino = (getattr(fiscal, "uf_destino", None) or "").strip().upper()
        fiscal_tipo_entidade = (getattr(fiscal, "tipo_entidade", None) or "").strip().upper()
        fiscal_cfop = getattr(fiscal, "cfop", None)

        ctx_uf_origem = (uf_origem or "").strip().upper()
        ctx_uf_destino = (uf_destino or "").strip().upper()
        ctx_tipo_entidade = (tipo_entidade or "").strip().upper()
        ctx_cfop = (getattr(cfop, "cfop_codi", None) or "").strip()

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
