from lxml import etree
import logging

logger = logging.getLogger(__name__)


class SefazResponseParser:
    NS = {
        "soap": "http://www.w3.org/2003/05/soap-envelope",
        "ws": "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4",
        "nfe": "http://www.portalfiscal.inf.br/nfe",
    }

    def parse(self, xml_str: str):
        logger.debug("SEFAZ XML RESPOSTA (bruto): %s", xml_str)

        if not xml_str or not str(xml_str).strip():
            return {
                "status": None,
                "motivo": "Resposta vazia da SEFAZ",
                "protocolo": None,
                "chave": None,
                "raw": xml_str,
            }

        try:
            root = etree.fromstring(xml_str.encode("utf-8"))
        except Exception as e:
            logger.error("Falha ao parsear XML de resposta da SEFAZ: %s", e)
            return {
                "status": None,
                "motivo": f"Erro ao parsear XML de resposta: {e}",
                "protocolo": None,
                "chave": None,
                "raw": xml_str,
            }

        ret = root.find(".//nfe:retEnviNFe", namespaces=self.NS)
        if ret is None:
            ret = root.find(".//nfe:retConsReciNFe", namespaces=self.NS)

        if ret is None:
            logger.warning("Não encontrei retEnviNFe / retConsReciNFe na resposta da SEFAZ")
            return {
                "status": None,
                "motivo": None,
                "protocolo": None,
                "chave": None,
                "raw": xml_str,
            }

        cStat = ret.findtext("nfe:cStat", namespaces=self.NS)
        xMotivo = ret.findtext("nfe:xMotivo", namespaces=self.NS)

        prot = ret.find(".//nfe:protNFe", namespaces=self.NS)
        protocolo = None
        chave = None
        if prot is not None:
            protocolo = prot.findtext(".//nfe:nProt", namespaces=self.NS)
            chave = prot.findtext(".//nfe:chNFe", namespaces=self.NS)

        logger.info(
            "SEFAZ retorno: cStat=%s, xMotivo=%s, protocolo=%s, chave=%s",
            cStat, xMotivo, protocolo, chave,
        )

        return {
            "status": cStat,
            "motivo": xMotivo,
            "protocolo": protocolo,
            "chave": chave,
            "raw": xml_str,
        }
