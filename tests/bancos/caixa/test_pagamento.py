import unittest
import sys
import types
import os


def install_stubs_caixa():
    from tests.utils.cnab_stubs import install_all_cnab_stubs
    install_all_cnab_stubs()
    # usar módulos já providos pelos stubs globais
    ret = types.ModuleType('cnab240.retornos.caixa')

    class Arquivo400:
        def as_txt(self):
            return '104\\n000123\\n1234567890'
    class HeaderArquivo: pass
    class Detalhe: pass
    class TrailerArquivo:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    class _Ret400:
        def __init__(self, caminho):
            self.titulos = [types.SimpleNamespace(nosso_numero='1234567890', valor_pago=200.0, data_pagamento=__import__('datetime').date(2024,3,1))]

    class _TituloRet:
        def __init__(self):
            self.nosso_numero = '1234567890'
            self.valor_pago = 200.0
            self.data_pagamento = __import__('datetime').date(2024, 3, 1)

    class CaixaRetorno:
        def __init__(self, caminho):
            self.titulos = [_TituloRet()]

    ret.CaixaRetorno = CaixaRetorno
    sys.modules['cnab400.tipos'].Arquivo400 = Arquivo400
    sys.modules['cnab400.itau'].HeaderArquivo = HeaderArquivo
    sys.modules['cnab400.itau'].Detalhe = Detalhe
    sys.modules['cnab400.itau'].TrailerArquivo = TrailerArquivo
    sys.modules['cnab400.retornos.itau'].ItauRetorno400 = _Ret400

    # remessa.caixa já configurada em install_all_cnab_stubs
    sys.modules['cnab240.retornos.caixa'] = ret
    # manter módulos já instalados pelos stubs globais


class DummyTitulo:
    def __init__(self):
        from datetime import date
        self.titu_clie = 123
        self.titu_titu = "000123"
        self.titu_seri = "A1"
        self.titu_parc = "001"
        self.titu_emis = date(2024, 1, 1)
        self.titu_venc = date(2024, 12, 31)
        self.titu_valo = 150.75
        self.titu_noss_nume = "1234567890"


class TestFluxoPagamentoCaixa(unittest.TestCase):
    def setUp(self):
        install_stubs_caixa()
        from boletos.services.cnab_service import CNABService
        from boletos.services.retorno_service import RetornoService
        from boletos.services.boleto_service import BoletoService
        self.CNABService = CNABService
        self.RetornoService = RetornoService
        self.BoletoService = BoletoService
        self.titulo = DummyTitulo()
        self.cedente = {"nome": "EMPRESA LTDA", "documento": "00.000.000/0001-91"}
        self.sacado = {"nome": "Cliente Y", "endereco": "Rua 2"}
        self.banco_cfg = {"codigo_banco": "104", "agencia": "1234", "conta": "56789", "dv": "0", "carteira": "SR", "logo_variation": "Colorido"}
        self.outdir = os.path.join("media", "tests", "bancos", "caixa")
        os.makedirs(self.outdir, exist_ok=True)

    def test_pdf_remessa_retorno(self):
        pdf_path = os.path.join(self.outdir, "boleto_caixa.pdf")
        self.BoletoService().gerar_pdf(self.titulo, self.cedente, self.sacado, self.banco_cfg, pdf_path)
        self.assertTrue(os.path.exists(pdf_path))
        self.assertGreater(os.path.getsize(pdf_path), 1000)

        txt240 = self.CNABService().gerar_remessa("240", self.banco_cfg, self.cedente, [self.titulo])
        self.assertTrue(len(txt240) > 0)

        dados = self.RetornoService().processar(os.path.join(self.outdir, "retorno.240"))
        self.assertTrue(len(dados) >= 1)
        self.assertEqual(dados[0]["nosso_numero"], self.titulo.titu_noss_nume)


if __name__ == "__main__":
    unittest.main()
