from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from boletos.services.online_banks.cora_service import CoraCobrancaService


class _Resp:
    def __init__(self, status=200, json_data=None, text=''):
        self.status_code = status
        self._json = json_data if json_data is not None else {}
        self.text = text if text else ('{}' if json_data is not None else '')
        self.content = b'%PDF-1.4 test' if self.text == 'PDF' else b''

    def json(self):
        return self._json


class CoraCobrancaServiceTests(SimpleTestCase):
    def _carteira(self):
        return SimpleNamespace(
            cart_webs_ssl_lib='https://api.stage.cora.com.br',
            cart_webs_clie_id='client-id',
            cart_webs_clie_secr='client-secret',
            cart_webs_user_key='',
            cart_webs_scop='invoice',
        )

    @patch('boletos.services.online_banks.base.requests.post')
    @patch('boletos.services.online_banks.cora_service.requests.post')
    def test_registrar_normaliza_campos_para_view(self, mock_post_cora, mock_post_token):
        mock_post_token.return_value = _Resp(json_data={'access_token': 'tok'})
        mock_post_cora.return_value = _Resp(json_data={
            'id': 'inv_123',
            'payment_options': {
                'bank_slip': {
                    'digitable': '123456',
                    'url': 'https://pdf.cora.com.br/boleto.pdf',
                    'our_number': '0001',
                },
                'pix': {'emv': 'pix-copia-cola'}
            }
        })

        service = CoraCobrancaService(self._carteira())
        data = service.registrar_boleto({'seuNumero': 'TIT/1', 'valor': 10.01, 'dataVencimento': '2026-04-30', 'pagador': {'nome': 'Cliente', 'documento': '12345678901'}})

        self.assertEqual(data.get('nossoNumero'), 'inv_123')
        self.assertEqual(data.get('linhaDigitavel'), '123456')
        self.assertEqual(data.get('linkBoleto'), 'https://pdf.cora.com.br/boleto.pdf')
        self.assertEqual((data.get('pix') or {}).get('copiaECola'), 'pix-copia-cola')

    @patch('boletos.services.online_banks.base.requests.post')
    @patch('boletos.services.online_banks.cora_service.requests.get')
    def test_consultar_normaliza_campos_para_view(self, mock_get_cora, mock_post_token):
        mock_post_token.return_value = _Resp(json_data={'access_token': 'tok'})
        mock_get_cora.return_value = _Resp(json_data={
            'id': 'inv_987',
            'payment_options': {
                'bank_slip': {
                    'digitable': '78910',
                    'url': 'https://pdf.cora.com.br/outro.pdf',
                }
            }
        })

        service = CoraCobrancaService(self._carteira())
        data = service.consultar_boleto('inv_987')

        self.assertEqual(data.get('nossoNumero'), 'inv_987')
        self.assertEqual(data.get('linhaDigitavel'), '78910')
        self.assertEqual(data.get('linkBoleto'), 'https://pdf.cora.com.br/outro.pdf')
