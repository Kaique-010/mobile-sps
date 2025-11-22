import types
import sys


def install_all_cnab_stubs():
    # Root packages as packages
    cnab240_root = types.ModuleType('cnab240'); cnab240_root.__path__ = []
    cnab240_tipos = types.ModuleType('cnab240.tipos')
    cnab240_remessa = types.ModuleType('cnab240.remessa'); cnab240_remessa.__path__ = []
    cnab240_retornos = types.ModuleType('cnab240.retornos'); cnab240_retornos.__path__ = []

    cnab400_root = types.ModuleType('cnab400'); cnab400_root.__path__ = []
    cnab400_tipos = types.ModuleType('cnab400.tipos')
    cnab400_retornos = types.ModuleType('cnab400.retornos'); cnab400_retornos.__path__ = []

    # cnab240 tipos
    class Arquivo:
        def __init__(self):
            self.header = None
            self.lotes = []
        def incluir_lote(self, arg):
            class Lote:
                def __init__(self):
                    self.registros = []
                def incluir_registro(self, r):
                    self.registros.append(r)
            lote = Lote()
            self.lotes.append(lote)
            return lote
        def as_txt(self):
            parts = []
            # header
            if self.header and hasattr(self.header, 'codigo_banco'):
                parts.append(str(getattr(self.header, 'codigo_banco')))
            # registros
            for lote in self.lotes:
                for r in getattr(lote, 'registros', []):
                    for fld in ('nosso_numero', 'numero_documento'):
                        v = getattr(r, fld, None)
                        if v:
                            parts.append(str(v))
            return '\n'.join(parts) or '240\nOK'

    cnab240_tipos.Arquivo = Arquivo

    # cnab240 remessa registros comuns
    def build_remessa_module(name):
        m = types.ModuleType(name)
        class Registro0:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
        class Registro1:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
        class Registro3P:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
        class Registro3Q:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
        m.Registro0 = Registro0
        m.Registro1 = Registro1
        m.Registro3P = Registro3P
        m.Registro3Q = Registro3Q
        return m

    cnab240_remessa_itau = build_remessa_module('cnab240.remessa.itau')
    cnab240_remessa_bradesco = build_remessa_module('cnab240.remessa.bradesco')
    cnab240_remessa_caixa = build_remessa_module('cnab240.remessa.caixa')
    cnab240_remessa_sicoob = build_remessa_module('cnab240.remessa.sicoob')
    cnab240_remessa_sicredi = build_remessa_module('cnab240.remessa.sicredi')

    # cnab240 retornos
    class _TituloRet:
        def __init__(self):
            import datetime
            self.nosso_numero = '1234567890'
            self.valor_pago = 100.0
            self.data_pagamento = datetime.date(2024, 1, 1)

    class ItauRetorno:
        def __init__(self, caminho):
            self.titulos = [_TituloRet()]

    cnab240_retornos.ItauRetorno = ItauRetorno

    def build_ret_module(name, clsname):
        m = types.ModuleType(name)
        cls = type(clsname, (), {
            '__init__': lambda self, caminho: setattr(self, 'titulos', [_TituloRet()])
        })
        setattr(m, clsname, cls)
        return m

    cnab240_ret_itau = build_ret_module('cnab240.retornos.itau', 'ItauRetorno')
    cnab240_ret_bradesco = build_ret_module('cnab240.retornos.bradesco', 'BradescoRetorno')
    cnab240_ret_caixa = build_ret_module('cnab240.retornos.caixa', 'CaixaRetorno')
    cnab240_ret_sicoob = build_ret_module('cnab240.retornos.sicoob', 'SicoobRetorno')
    cnab240_ret_sicredi = build_ret_module('cnab240.retornos.sicredi', 'SicrediRetorno')

    # cnab400 tipos
    class Arquivo400:
        def __init__(self):
            self.header = None
            self.trailer = None
            self._detalhes = []
        def incluir_detalhe(self, d):
            self._detalhes.append(d)
        def as_txt(self):
            return '400\nOK'

    cnab400_tipos.Arquivo400 = Arquivo400

    # cnab400 libs por banco
    def build_400_bank(name):
        m = types.ModuleType(name)
        class HeaderArquivo: pass
        class Detalhe: pass
        class TrailerArquivo:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
        m.HeaderArquivo = HeaderArquivo
        m.Detalhe = Detalhe
        m.TrailerArquivo = TrailerArquivo
        return m

    cnab400_itau = build_400_bank('cnab400.itau')
    cnab400_bradesco = build_400_bank('cnab400.bradesco')
    cnab400_caixa = build_400_bank('cnab400.caixa')
    cnab400_sicoob = build_400_bank('cnab400.sicoob')
    cnab400_sicredi = build_400_bank('cnab400.sicredi')

    # cnab400 retornos por banco
    def build_400_ret(name, clsname):
        m = types.ModuleType(name)
        import datetime, types as _t
        cls = type(clsname, (), {
            '__init__': lambda self, caminho: setattr(self, 'titulos', [_t.SimpleNamespace(nosso_numero='1234567890', valor_pago=100.0, data_pagamento=datetime.date(2024,1,1))])
        })
        setattr(m, clsname, cls)
        return m

    cnab400_ret_itau = build_400_ret('cnab400.retornos.itau', 'ItauRetorno400')
    cnab400_ret_bradesco = build_400_ret('cnab400.retornos.bradesco', 'BradescoRetorno400')
    cnab400_ret_caixa = build_400_ret('cnab400.retornos.caixa', 'CaixaRetorno400')
    cnab400_ret_sicoob = build_400_ret('cnab400.retornos.sicoob', 'SicoobRetorno400')
    cnab400_ret_sicredi = build_400_ret('cnab400.retornos.sicredi', 'SicrediRetorno400')

    # Registrar no sys.modules
    sys.modules['cnab240'] = cnab240_root
    sys.modules['cnab240.tipos'] = cnab240_tipos
    sys.modules['cnab240.remessa'] = cnab240_remessa
    sys.modules['cnab240.remessa.itau'] = cnab240_remessa_itau
    sys.modules['cnab240.remessa.bradesco'] = cnab240_remessa_bradesco
    sys.modules['cnab240.remessa.caixa'] = cnab240_remessa_caixa
    sys.modules['cnab240.remessa.sicoob'] = cnab240_remessa_sicoob
    sys.modules['cnab240.remessa.sicredi'] = cnab240_remessa_sicredi

    sys.modules['cnab240.retornos'] = cnab240_retornos
    sys.modules['cnab240.retornos.itau'] = cnab240_ret_itau
    sys.modules['cnab240.retornos.bradesco'] = cnab240_ret_bradesco
    sys.modules['cnab240.retornos.caixa'] = cnab240_ret_caixa
    sys.modules['cnab240.retornos.sicoob'] = cnab240_ret_sicoob
    sys.modules['cnab240.retornos.sicredi'] = cnab240_ret_sicredi

    sys.modules['cnab400'] = cnab400_root
    sys.modules['cnab400.tipos'] = cnab400_tipos
    sys.modules['cnab400.itau'] = cnab400_itau
    sys.modules['cnab400.bradesco'] = cnab400_bradesco
    sys.modules['cnab400.caixa'] = cnab400_caixa
    sys.modules['cnab400.sicoob'] = cnab400_sicoob
    sys.modules['cnab400.sicredi'] = cnab400_sicredi

    sys.modules['cnab400.retornos'] = cnab400_retornos
    sys.modules['cnab400.retornos.itau'] = cnab400_ret_itau
    sys.modules['cnab400.retornos.bradesco'] = cnab400_ret_bradesco
    sys.modules['cnab400.retornos.caixa'] = cnab400_ret_caixa
    sys.modules['cnab400.retornos.sicoob'] = cnab400_ret_sicoob
    sys.modules['cnab400.retornos.sicredi'] = cnab400_ret_sicredi

