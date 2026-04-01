from types import SimpleNamespace

from django.test import SimpleTestCase

from boletos.Web.views.online_cbv import _extract, _resolve_bank_code


class BoletoOnlineHelpersTests(SimpleTestCase):
    def test_extract_retorna_primeiro_caminho_valido(self):
        data = {
            'codigoBarras': {'linhaDigitavel': '123'},
            'pix': {'copiaECola': 'pix-code'}
        }
        self.assertEqual(_extract(data, 'linhaDigitavel', 'codigoBarras.linhaDigitavel'), '123')

    def test_extract_retorna_none_quando_nao_encontra(self):
        self.assertIsNone(_extract({'x': 1}, 'a.b', 'c'))

    def test_resolve_bank_code_usando_entidade(self):
        entidade = SimpleNamespace(enti_banc='748')
        self.assertEqual(_resolve_bank_code(entidade), '748')
