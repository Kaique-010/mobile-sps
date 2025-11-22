import unittest
import sys
import types
import os


def install_stubs_itau():
    from tests.utils.cnab_stubs import install_all_cnab_stubs
    install_all_cnab_stubs()

    # stubs globais já fornecem cnab240.remessa.itau e cnab240.tipos.Arquivo

    class Arquivo400:
        def __init__(self):
            self.registros = []
        def add(self, r):
            self.registros.append(r)
        def as_txt(self):
            return '341\\n000123\\n1234567890'

    class HeaderArquivo:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    class Detalhe:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    class TrailerArquivo:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    class _Ret400:
        def __init__(self, caminho):
            from datetime import date
            self.titulos = [types.SimpleNamespace(nosso_numero='1234567890', valor_pago=100.5, data_pagamento=date(2024,2,1))]

    class _TituloRet:
        def __init__(self, nosso_numero, valor_pago, data_pagamento):
            self.nosso_numero = nosso_numero
            self.valor_pago = valor_pago
            self.data_pagamento = data_pagamento

    class ItauRetorno:
        def __init__(self, caminho):
            from datetime import date
            self.titulos = [_TituloRet('1234567890', 100.5, date(2024, 2, 1))]

    sys.modules['cnab400.tipos'].Arquivo400 = Arquivo400
    sys.modules['cnab400.itau'].HeaderArquivo = HeaderArquivo
    sys.modules['cnab400.itau'].Detalhe = Detalhe
    sys.modules['cnab400.itau'].TrailerArquivo = TrailerArquivo
    sys.modules['cnab400.retornos.itau'].ItauRetorno400 = _Ret400
    sys.modules['cnab240.retornos'].ItauRetorno = ItauRetorno

    # manter módulos já instalados pelo stub utilitário


class DummyTitulo:
    def __init__(self):
        from datetime import date
        self.titu_clie = 123
        self.titu_titu = "000123"
        self.titu_seri = "A1"
        self.titu_parc = "001"
        self.titu_emis = date(2024, 1, 1)
        self.titu_venc = date(2024, 12, 31)
        self.titu_valo = 100.50
        self.titu_noss_nume = "1234567890"


class TestFluxoPagamentoItau(unittest.TestCase):
    def setUp(self):
        install_stubs_itau()
        from boletos.services.cnab_service import CNABService
        from boletos.services.retorno_service import RetornoService
        from boletos.services.boleto_service import BoletoService
        self.CNABService = CNABService
        self.RetornoService = RetornoService
        self.BoletoService = BoletoService
        self.titulo = DummyTitulo()
        self.cedente = {"nome": "EMPRESA LTDA", "documento": "00.000.000/0001-91"}
        self.sacado = {"nome": "Cliente X", "endereco": "Rua 1"}
        self.banco_cfg = {"codigo_banco": "341", "agencia": "1234", "conta": "56789", "dv": "0", "carteira": "109", "logo_variation": "Colorido"}
        self.outdir = os.path.join("media", "tests", "bancos", "itau")
        os.makedirs(self.outdir, exist_ok=True)

    def test_pdf_remessa_retorno(self):
        # PDF
        pdf_path = os.path.join(self.outdir, "boleto_itau.pdf")
        self.BoletoService().gerar_pdf(self.titulo, self.cedente, self.sacado, self.banco_cfg, pdf_path)
        self.assertTrue(os.path.exists(pdf_path))
        self.assertGreater(os.path.getsize(pdf_path), 1000)

        # Remessa
        txt240 = self.CNABService().gerar_remessa("240", self.banco_cfg, self.cedente, [self.titulo])
        self.assertTrue(len(txt240) > 0)
        self.assertIn(self.titulo.titu_noss_nume, txt240)

        # Retorno
        dados = self.RetornoService().processar(os.path.join(self.outdir, "retorno.240"))
        self.assertTrue(len(dados) >= 1)
        self.assertEqual(dados[0]["nosso_numero"], self.titulo.titu_noss_nume)


if __name__ == "__main__":
    unittest.main()
