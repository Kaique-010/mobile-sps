import unittest
import os

from boletos.services.boleto_service import BoletoService
from boletos.services.validation_service import validate_boleto, build_barcode_data, render_barcode_image


class DummyTitulo:
    def __init__(self, numero, venc, valor, nosso):
        self.titu_titu = numero
        self.titu_emis = venc
        self.titu_venc = venc
        self.titu_valo = valor
        self.titu_noss_nume = nosso
        self.titu_clie = 1


class TestValidacaoBoletos(unittest.TestCase):
    def setUp(self):
        from datetime import date
        self.titulo = DummyTitulo("000123", date(2025, 12, 31), 123.45, "12345678901")
        self.cedente = {"nome": "EMPRESA LTDA", "documento": "00.000.000/0001-91"}
        self.sacado = {"nome": "Cliente Teste", "endereco": "Rua 1"}
        self.outdir = os.path.join("media", "tests", "boletos", "validacao")
        os.makedirs(self.outdir, exist_ok=True)

    def _run_for(self, banco_cfg):
        path = os.path.join(self.outdir, f"boleto_{banco_cfg['codigo_banco']}.pdf")
        BoletoService().gerar_pdf(self.titulo, self.cedente, self.sacado, banco_cfg, path)
        root_path = os.path.join(os.getcwd(), f"boleto_{banco_cfg['codigo_banco']}.pdf")
        BoletoService().gerar_pdf(self.titulo, self.cedente, self.sacado, banco_cfg, root_path)
        v = validate_boleto(self.cedente, self.sacado, banco_cfg, self.titulo)
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 1000)
        self.assertEqual(len(v['missing']), 0)
        self.assertTrue(v['barcode']['len_ok'])
        self.assertTrue(v['barcode']['dv_ok'])
        codigo = build_barcode_data(banco_cfg, self.titulo)
        img = render_barcode_image(codigo)
        self.assertTrue(img is not None)

    def test_itau(self):
        banco_cfg = {"codigo_banco": "341", "agencia": "1234", "conta": "56789012", "dv": "0", "carteira": "109", "logo_variation": "Colorido"}
        self._run_for(banco_cfg)

    def test_bradesco(self):
        banco_cfg = {"codigo_banco": "237", "agencia": "1234", "conta": "56789012", "dv": "0", "carteira": "09", "logo_variation": "Colorido"}
        self._run_for(banco_cfg)

    def test_caixa(self):
        banco_cfg = {"codigo_banco": "104", "agencia": "1234", "conta": "56789012", "dv": "0", "carteira": "SR", "logo_variation": "Colorido"}
        self._run_for(banco_cfg)

    def test_sicoob(self):
        banco_cfg = {"codigo_banco": "756", "agencia": "1234", "conta": "56789012", "dv": "0", "carteira": "01", "logo_variation": "Colorido"}
        self._run_for(banco_cfg)

    def test_sicredi(self):
        banco_cfg = {"codigo_banco": "748", "agencia": "1234", "conta": "56789012", "dv": "0", "carteira": "01", "logo_variation": "Colorido"}
        self._run_for(banco_cfg)


if __name__ == "__main__":
    unittest.main()
