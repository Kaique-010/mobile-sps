import unittest
from unittest.mock import MagicMock, patch
import requests
from requests.adapters import HTTPAdapter
from Notas_Fiscais.emissao.sefaz_client import SefazClient

class TestSefazIntegration(unittest.TestCase):
    def setUp(self):
        self.client = SefazClient(
            cert_pem_path="dummy_cert.pem",
            key_pem_path="dummy_key.pem",
            url="https://nfe.sefaz.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx"
        )
        self.xml_dummy = "<NFe>...</NFe>"

    def test_retry_configuration(self):
        """
        Verifica se a estratégia de Retry foi configurada corretamente na Sessão.
        """
        adapter = self.client.session.get_adapter("https://")
        self.assertIsInstance(adapter, HTTPAdapter)
        
        retry = adapter.max_retries
        self.assertEqual(retry.total, 3)
        self.assertEqual(retry.backoff_factor, 1)
        self.assertIn(500, retry.status_forcelist)
        self.assertIn(503, retry.status_forcelist)
        self.assertIn(429, retry.status_forcelist)

    @patch("requests.Session.post")
    def test_envio_sucesso(self, mock_post):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<retorno>OK</retorno>"
        mock_post.return_value = mock_response

        # Execute
        resp = self.client.enviar_xml(self.xml_dummy, cuf="43")

        # Assert
        self.assertEqual(resp, "<retorno>OK</retorno>")
        mock_post.assert_called_once()

    @patch("requests.Session.post")
    def test_erro_fatal_propaga_excecao(self, mock_post):
        """
        Verifica se, após falhar (seja por timeout ou erro de conexão),
        o cliente loga e propaga a exceção.
        """
        mock_post.side_effect = requests.exceptions.ConnectTimeout("Connection timed out")

        with self.assertRaises(requests.exceptions.ConnectTimeout):
            self.client.enviar_xml(self.xml_dummy, cuf="43")
            
    @patch("requests.Session.post")
    def test_status_400_raises_error(self, mock_post):
        # 400 Bad Request
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        
        # raise_for_status simulation
        def raise_http_error():
            raise requests.exceptions.HTTPError("400 Client Error")
        mock_response.raise_for_status = raise_http_error
        
        mock_post.return_value = mock_response

        with self.assertRaises(requests.exceptions.HTTPError):
            self.client.enviar_xml(self.xml_dummy, cuf="43")
