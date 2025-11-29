import requests

class SefazClient:

    def __init__(self, cert_pem, key_pem, url, verify=True):
        self.cert = (cert_pem, key_pem)
        self.url = url
        self.verify = verify

    def enviar_xml(self, xml_assinado):
        envelope = f"""
        <soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
            <soap12:Body>
                <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4">
                    {xml_assinado}
                </nfeDadosMsg>
            </soap12:Body>
        </soap12:Envelope>
        """

        headers = {
            "Content-Type": "application/soap+xml; charset=utf-8"
        }

        response = requests.post(
            self.url,
            data=envelope.encode("utf-8"),
            headers=headers,
            cert=self.cert,
            timeout=30,
            verify=self.verify,
        )

        return response.text
