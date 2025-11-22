class _StubAdapter:
    def processar_retorno(self, caminho):
        return []



class RetornoService:
    def processar(self, caminho):
        adapter = self.resolver_adapter(caminho)
        return adapter.processar_retorno(caminho)

    def resolver_adapter(self, caminho):
        try:
            if caminho.endswith(".240"):
                from ..adaptadores.itau.itau240 import ItauCnab240Adapter
                return ItauCnab240Adapter()
            if caminho.endswith(".400"):
                from ..adaptadores.itau.itau400 import ItauCnab400Adapter
                return ItauCnab400Adapter()
        except Exception:
            return _StubAdapter()
        return _StubAdapter()
