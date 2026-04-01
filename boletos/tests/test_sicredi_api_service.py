from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from boletos.services.sicredi_api_service import SicrediCobrancaService


class SicrediCobrancaServiceTests(TestCase):
    def _carteira(self):
        return SimpleNamespace(
            cart_webs_clie_id="client-id",
            cart_webs_clie_secr="client-secret",
            cart_webs_scop="cobranca",
            cart_webs_user_key="api-key-123",
            cart_webs_ssl_lib="sandbox",
        )

    @patch("boletos.services.sicredi_api_service.requests.post")
    def test_get_access_token_envia_client_credentials_com_api_key(self, post_mock):
        token_response = Mock(status_code=200)
        token_response.json.return_value = {"access_token": "token-abc"}
        post_mock.return_value = token_response

        service = SicrediCobrancaService(self._carteira())
        token = service.get_access_token()

        self.assertEqual(token, "token-abc")
        _, kwargs = post_mock.call_args
        self.assertEqual(kwargs["data"]["grant_type"], "password")
        self.assertEqual(kwargs["data"]["username"], "client-id")
        self.assertEqual(kwargs["data"]["password"], "client-secret")
        self.assertEqual(kwargs["data"]["scope"], "cobranca")
        self.assertEqual(kwargs["headers"]["x-api-key"], "api-key-123")

    @patch("boletos.services.sicredi_api_service.requests.post")
    def test_registrar_boleto_usa_endpoint_e_bearer_token(self, post_mock):
        token_response = Mock(status_code=200)
        token_response.json.return_value = {"access_token": "token-abc"}

        boleto_response = Mock(status_code=201, text='{"nossoNumero":"123"}')
        boleto_response.json.return_value = {"nossoNumero": "123"}

        post_mock.side_effect = [token_response, boleto_response]

        service = SicrediCobrancaService(self._carteira())
        result = service.registrar_boleto({"seuNumero": "ABC-1"})

        self.assertEqual(result["nossoNumero"], "123")
        self.assertEqual(post_mock.call_count, 2)

        token_call = post_mock.call_args_list[0]
        boleto_call = post_mock.call_args_list[1]

        self.assertIn("/auth/openapi/token", token_call.args[0])
        self.assertIn("/cobranca/boleto/v1/boletos", boleto_call.args[0])
        self.assertEqual(boleto_call.kwargs["headers"]["Authorization"], "Bearer token-abc")
        self.assertEqual(boleto_call.kwargs["json"]["seuNumero"], "ABC-1")

    @patch("boletos.services.sicredi_api_service.requests.patch")
    @patch("boletos.services.sicredi_api_service.requests.post")
    def test_cancelar_boleto_reaproveita_fluxo_de_baixa(self, post_mock, patch_mock):
        token_response = Mock(status_code=200)
        token_response.json.return_value = {"access_token": "token-abc"}
        post_mock.return_value = token_response

        baixa_response = Mock(status_code=200, text='{"ok":true}')
        baixa_response.json.return_value = {"ok": True}
        patch_mock.return_value = baixa_response

        service = SicrediCobrancaService(self._carteira())
        result = service.cancelar_boleto("123", payload={})

        self.assertEqual(result, {"ok": True})
        self.assertIn("/cobranca/boleto/v1/boletos/123/cancelamento", patch_mock.call_args.args[0])
        self.assertEqual(post_mock.call_count, 1)

    @patch("boletos.services.sicredi_api_service.requests.patch")
    @patch("boletos.services.sicredi_api_service.requests.post")
    def test_cancelar_boleto_faz_fallback_para_baixa_quando_cancelamento_nao_disponivel(self, post_mock, patch_mock):
        token_response = Mock(status_code=200)
        token_response.json.return_value = {"access_token": "token-abc"}
        post_mock.return_value = token_response

        cancelamento_404 = Mock(status_code=404, text='not found')
        baixa_200 = Mock(status_code=200, text='{"ok":true}')
        baixa_200.json.return_value = {"ok": True}
        patch_mock.side_effect = [cancelamento_404, baixa_200]

        service = SicrediCobrancaService(self._carteira())
        result = service.cancelar_boleto("123", payload={})

        self.assertEqual(result, {"ok": True})
        self.assertIn("/cobranca/boleto/v1/boletos/123/cancelamento", patch_mock.call_args_list[0].args[0])
        self.assertIn("/cobranca/boleto/v1/boletos/123/baixa", patch_mock.call_args_list[1].args[0])
        self.assertEqual(post_mock.call_count, 1)
