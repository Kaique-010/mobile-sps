from unittest.mock import patch, MagicMock
from django.test import SimpleTestCase
from core.utils import get_db_from_slug
from transportes.services.sefaz_gateway import SefazGateway, CTE_NS
import re


class EmissaoCTEFlowTest(SimpleTestCase):
    def setUp(self):
        get_db_from_slug("saveweb001")

    def _fake_success_response(self):
        return (
            "<retEnviCTe xmlns=\"http://www.portalfiscal.inf.br/cte\">"
            "<cStat>100</cStat>"
            "<xMotivo>Autorizado o uso do CT-e</xMotivo>"
            "<protCTe><infProt><nProt>1234567890</nProt></infProt></protCTe>"
            "</retEnviCTe>"
        ).encode("utf-8")

    def _should_accept_envelope(self, envelope: str) -> bool:
        has_op_wrapper = "<ws:cteRecepcaoSinc" in envelope
        has_msg = "<ws:cteDadosMsg" in envelope
        body_payload_is_base64 = not re.search(r"<CTe|<enviCTe", envelope)
        return has_op_wrapper and has_msg and body_payload_is_base64

    @patch.object(SefazGateway, "_get_url", return_value="https://example.invalid/CTeRecepcaoSincV4")
    @patch.object(SefazGateway, "_get_cert_pem_and_key_pem", return_value=("", ""))
    @patch.object(SefazGateway, "_ambiente", return_value="2")
    @patch.object(SefazGateway, "_uf", return_value="PR")
    @patch.object(SefazGateway, "_cuf_from_filial", return_value="41")
    def test_envio_usa_wrapper_operacao_e_payload_gzip_base64(
        self, *_mocks
    ):
        cte = MagicMock()
        cte.numero = "1"
        cte.filial = MagicMock()
        cte.filial.empr_esta = "PR"
        cte.filial.empr_codi_uf = "41"

        gw = SefazGateway(cte)

        def fake_post(url, envelope, cert, proxies, soap_action, soap_version):
            if self._should_accept_envelope(envelope):
                return self._fake_success_response()
            raise Exception("cStat 244: Falha na descompactacao da area de dados")

        with patch.object(gw, "_post_soap", side_effect=fake_post):
            xml_cte_min = (
                f"<CTe xmlns=\"{CTE_NS}\">"
                "<infCte><ide><cUF>41</cUF></ide></infCte>"
                "</CTe>"
            )
            resultado = gw.enviar(xml_cte_min)
            self.assertEqual(resultado.get("status"), "autorizado")
            self.assertEqual(resultado.get("protocolo"), "1234567890")
