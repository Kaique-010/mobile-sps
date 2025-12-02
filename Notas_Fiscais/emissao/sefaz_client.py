import logging
import requests

logger = logging.getLogger(__name__)

NFE_NS = "http://www.portalfiscal.inf.br/nfe"
SOAP_ENV = "http://www.w3.org/2003/05/soap-envelope"
WSDL_NS = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4"


class SefazClient:
    def __init__(self, cert_pem_path: str, key_pem_path: str, url: str, verify=True):
        self.cert = (cert_pem_path, key_pem_path)
        self.url = url
        self.verify = verify

    def _build_envelope(self, xml_envi_nfe: str, cuf: str) -> str:
        versao_dados = "4.00"
        envelope = f"""
<env:Envelope xmlns:env="{SOAP_ENV}">
  <env:Header>
    <ws:nfeCabecMsg xmlns:ws="{WSDL_NS}">
      <ws:cUF>{cuf}</ws:cUF>
      <ws:versaoDados>{versao_dados}</ws:versaoDados>
    </ws:nfeCabecMsg>
  </env:Header>
  <env:Body>
    <ws:nfeDadosMsg xmlns:ws="{WSDL_NS}">
      {xml_envi_nfe}
    </ws:nfeDadosMsg>
  </env:Body>
</env:Envelope>
""".strip()
        return envelope

    def enviar_xml(self, xml_envi_nfe: str, cuf: str = None) -> str:
        """
        Envia o XML enviNFe para o WebService NFeAutorizacao4.
        Retorna o XML de resposta (string).
        """
        if not cuf:
            # tentativa best-effort de extrair do XML
            try:
                from lxml import etree
                ns = {"nfe": NFE_NS}
                r = etree.fromstring(xml_envi_nfe.encode("utf-8"))
                cuf = r.findtext(".//nfe:cUF", namespaces=ns)
            except Exception:
                cuf = ""

        envelope = self._build_envelope(xml_envi_nfe, cuf)

        headers = {
            "Content-Type": "application/soap+xml; charset=utf-8",
        }

        logger.debug("=== SEFAZ REQUEST ===")
        logger.debug("URL: %s", self.url)
        logger.debug("cUF: %s", cuf)
        logger.debug("ENVELOPE:\n%s", envelope)

        resp = requests.post(
            self.url,
            data=envelope.encode("utf-8"),
            headers=headers,
            cert=self.cert,
            verify=self.verify,
            timeout=30,
        )

        logger.debug("=== SEFAZ RESPONSE ===")
        logger.debug("STATUS: %s", resp.status_code)
        logger.debug("CONTENT:\n%s", resp.text)

        resp.raise_for_status()

        return resp.text
