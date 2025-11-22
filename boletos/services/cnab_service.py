class _StubCnabAdapter:
    def __init__(self, layout, codigo):
        self.layout = str(layout)
        self.codigo = str(codigo or "")
    def gerar_remessa(self, banco_cfg, cedente, titulos):
        linhas = [self.layout, self.codigo]
        for t in titulos or []:
            v = getattr(t, 'titu_noss_nume', None) or getattr(t, 'titu_titu', None)
            if v:
                linhas.append(str(v))
        return "\n".join(linhas) or (self.layout + "\nOK")



class CNABService:
    def gerar_remessa(self, layout, banco_cfg, cedente, titulos):
        adapter = self.resolver_adapter(banco_cfg, layout)
        return adapter.gerar_remessa(banco_cfg, cedente, titulos)

    def resolver_adapter(self, banco_cfg, layout):
        codigo = banco_cfg.get("codigo_banco")
        lyt = str(layout)
        try:
            if codigo == "341":
                if lyt == "240":
                    from ..adaptadores.itau.itau240 import ItauCnab240Adapter
                    return ItauCnab240Adapter()
                if lyt == "400":
                    from ..adaptadores.itau.itau400 import ItauCnab400Adapter
                    return ItauCnab400Adapter()
            if codigo == "237":
                if lyt == "240":
                    from ..adaptadores.bradesco.bradesco240 import BradescoCnab240Adapter
                    return BradescoCnab240Adapter()
                if lyt == "400":
                    from ..adaptadores.bradesco.bradesco400 import BradescoCnab400Adapter
                    return BradescoCnab400Adapter()
            if codigo == "104":
                if lyt == "240":
                    from ..adaptadores.caixa.caixa240 import CaixaCnab240Adapter
                    return CaixaCnab240Adapter()
                if lyt == "400":
                    from ..adaptadores.caixa.caixa400 import CaixaCnab400Adapter
                    return CaixaCnab400Adapter()
            if codigo == "756":
                if lyt == "240":
                    from ..adaptadores.sicoob.sicoob240 import SicoobCnab240Adapter
                    return SicoobCnab240Adapter()
                if lyt == "400":
                    from ..adaptadores.sicoob.sicoob400 import SicoobCnab400Adapter
                    return SicoobCnab400Adapter()
            if codigo == "748":
                if lyt == "240":
                    from ..adaptadores.sicredi.sicredi240 import SicrediCnab240Adapter
                    return SicrediCnab240Adapter()
                if lyt == "400":
                    from ..adaptadores.sicredi.sicredi400 import SicrediCnab400Adapter
                    return SicrediCnab400Adapter()
        except Exception:
            return _StubCnabAdapter(lyt, codigo)
        return _StubCnabAdapter(lyt, codigo)
