from django.test import SimpleTestCase

from boletos.Web.views.online_cbv import _extract


class BoletoOnlineHelpersTests(SimpleTestCase):
    def test_extract_retorna_primeiro_caminho_valido(self):
        data = {
            'codigoBarras': {'linhaDigitavel': '123'},
            'pix': {'copiaECola': 'pix-code'}
        }
        self.assertEqual(_extract(data, 'linhaDigitavel', 'codigoBarras.linhaDigitavel'), '123')

    def test_extract_retorna_none_quando_nao_encontra(self):
        self.assertIsNone(_extract({'x': 1}, 'a.b', 'c'))
