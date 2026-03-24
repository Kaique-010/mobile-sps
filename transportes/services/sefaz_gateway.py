import logging
import os
import tempfile
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from lxml import etree
from cryptography.hazmat.primitives.serialization import (
    pkcs12,
    Encoding,
    PrivateFormat,
    NoEncryption,
)

from lxml import etree
import gzip
import base64
from transportes.models import Cte
from Licencas.models import Filiais
from Notas_Fiscais.infrastructure.certificado_loader import CertificadoLoader

logger = logging.getLogger(__name__)

CTE_NS = "http://www.portalfiscal.inf.br/cte"
SOAP_ENV = "http://www.w3.org/2003/05/soap-envelope"

URLS_SEFAZ_CTE = {
    "PR": {
        "producao": {
            "recepcao_sinc": "https://cte.fazenda.pr.gov.br/cte4/CTeRecepcaoSincV4",
            "consulta": "https://cte.fazenda.pr.gov.br/cte4/CTeConsultaV4",
        },
        "homologacao": {
            "recepcao_sinc": "https://homologacao.cte.fazenda.pr.gov.br/cte4/CTeRecepcaoSincV4",
            "consulta": "https://homologacao.cte.fazenda.pr.gov.br/cte4/CTeConsultaV4",
        },
    },
}


class SefazGateway:
    def __init__(self, cte: Cte):
        self.cte = cte
        self.filial = None
        self._carregar_filial()
        logger.info(f"Filial carregada: {self.filial}")

    def _carregar_filial(self):
        db_alias = self.cte._state.db or "default"
        self.filial = (
            Filiais.objects.using(db_alias)
            .filter(empr_empr=self.cte.empresa, empr_codi=self.cte.filial)
            .first()
        )
        if not self.filial:
            raise Exception("Filial não encontrada.")

    # ---------------- ENVIO ----------------
    
    def validar_xml(xml: str):
        try:
            etree.fromstring(xml.encode())
            return True
        except Exception as e:
            raise Exception(f"XML inválido: {e}")

    def enviar(self, xml_assinado: str) -> dict:
        ambiente = self._ambiente()
        cert, key = self._get_cert_pem_and_key_pem()
        uf = self._uf()

        url = self._get_url(uf, ambiente, "recepcao_sinc")
        wsdl_ns = "http://www.portalfiscal.inf.br/cte/wsdl/CTeRecepcaoSincV4"

        cuf = self._cuf_from_cte_xml(xml_assinado) or self._cuf_from_filial()
        xml_payload = (xml_assinado or "").strip()
        try:
            root = etree.fromstring(xml_payload.encode("utf-8"))
            def _find_text(tag):
                el = root.find(f".//{{*}}{tag}")
                return (el.text or "").strip() if el is not None else ""
            xnome_emit = root.find(".//{*}emit/{*}xNome")
            xnome_rem  = root.find(".//{*}rem/{*}xNome")
            xnome_dest = root.find(".//{*}dest/{*}xNome")
            val_emit = (xnome_emit.text or "").strip() if xnome_emit is not None else ""
            val_rem  = (xnome_rem.text or "").strip() if xnome_rem is not None else ""
            val_dest = (xnome_dest.text or "").strip() if xnome_dest is not None else ""
            tp_amb_cte = _find_text("tpAmb")
            esperado = "CTE EMITIDO EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL"
            logger.info(f"tpAmb={tp_amb_cte} | xNome emit={val_emit} rem={val_rem} dest={val_dest} | esperado={esperado}")
        except Exception:
            pass
        logger.info("XML FINAL (CTeRecepcaoSincV4):")
        logger.info(xml_payload[:500])
        print(xml_payload)

        envelope = self._build_envelope(
            xml_payload,
            cuf=cuf,
            wsdl_ns=wsdl_ns,
            versao_dados="4.00",
            operation="cteRecepcaoSinc"
        )

        resp = self._post_soap(
            url=url,
            envelope=envelope,
            cert=(cert, key),
        )

        return self._processar_retorno_xml(resp)

    # ---------------- SOAP ----------------

    def _build_envelope(self, xml_payload, *, cuf, wsdl_ns, versao_dados, operation):
        xml_payload_txt = (xml_payload or "").strip()
        xml_bytes = xml_payload_txt.encode("utf-8")
        logger.info(f"XML para comprimir (primeiros 200 chars): {repr(xml_payload_txt[:200])}")
        logger.info(f"XML começa com <CTe: {xml_payload_txt.startswith('<CTe') or xml_payload_txt.startswith('<ns0:CTe')}")
        
        try:
            gz = gzip.compress(xml_bytes, mtime=0)
        except TypeError:
            gz = gzip.compress(xml_bytes)
        
        payload = base64.b64encode(gz).decode("ascii")

        return f"""<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
                    <soap12:Header>
                    <cteCabecMsg xmlns="{wsdl_ns}">
                    <cUF>{cuf}</cUF>
                    <versaoDados>{versao_dados}</versaoDados>
                    </cteCabecMsg>
                    </soap12:Header>
                    <soap12:Body>
                    <{operation} xmlns="{wsdl_ns}">
                    <cteDadosMsg>{payload}</cteDadosMsg>
                    </{operation}>
                    </soap12:Body>
                    </soap12:Envelope>"""

    def _post_soap(self, *, url: str, envelope: str, cert): 

        
        session = requests.Session()
        

        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 502, 503, 504],
            allowed_methods=["POST"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)

        headers = {
                        "Content-Type": "application/soap+xml; charset=utf-8",
                        "Accept": "application/soap+xml"
                    }
        resp = session.post(
            url,
            data=envelope.encode("utf-8"),
            headers=headers,
            cert=cert,
            verify=self._resolve_verify(),
            timeout=30,
        )

        if not resp.content:
            raise Exception("Sem resposta SEFAZ")
        logger.info(f"RETORNO SEFAZ RAW: {resp.content.decode(errors='ignore')}")

        return resp.content

    # ---------------- HELPERS ----------------

    def _ambiente(self):
        val = str(getattr(self.filial, "empr_ambi_cte", "2"))
        return "1" if val == "1" else "2"

    def _uf(self):
        uf = getattr(self.filial, "empr_esta", "")
        if not uf:
            raise Exception("UF não definida")
        return uf

    def _cuf_from_filial(self):
        return str(getattr(self.filial, "empr_codi_uf", "")).zfill(2)

    def _cuf_from_cte_xml(self, xml):
        try:
            root = etree.fromstring(xml.encode())
            return root.findtext(".//{*}cUF")
        except:
            return ""

    def _get_url(self, uf, ambiente, servico):
        amb = "producao" if ambiente == "1" else "homologacao"
        return URLS_SEFAZ_CTE[uf][amb][servico]

    def _resolve_verify(self):
        return False  # homologação geralmente precisa

    def _get_cert_pem_and_key_pem(self):
        caminho, senha = CertificadoLoader(self.filial).load()

        with open(caminho, "rb") as f:
            pfx = f.read()

        key, cert, _ = pkcs12.load_key_and_certificates(
            pfx,
            senha.encode() if senha else None
        )

        cert_pem = cert.public_bytes(Encoding.PEM)
        key_pem = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())

        cert_file = tempfile.NamedTemporaryFile(delete=False)
        cert_file.write(cert_pem)
        cert_file.close()

        key_file = tempfile.NamedTemporaryFile(delete=False)
        key_file.write(key_pem)
        key_file.close()

        return cert_file.name, key_file.name

    def _montar_envi_cte(self, xml):
        root = etree.fromstring(xml.encode())

        # GARANTE que o root é CTe com namespace correto
        if not root.tag.endswith("CTe"):
            raise Exception("XML deve ter <CTe> como raiz")

        # força namespace correto no CTe (CRÍTICO)
        if not root.tag.startswith("{"):
            root.tag = f"{{{CTE_NS}}}CTe"

        # força namespace nos filhos que perderam (seguro)
        for el in root.iter():
            if not el.tag.startswith("{"):
                el.tag = f"{{{CTE_NS}}}{el.tag}"

        envi = etree.Element(f"{{{CTE_NS}}}enviCTe", nsmap={None: CTE_NS})
        envi.set("versao", "4.00")

        etree.SubElement(envi, f"{{{CTE_NS}}}idLote").text = str(self.cte.numero or "1")
        etree.SubElement(envi, f"{{{CTE_NS}}}indSinc").text = "1"

        envi.append(root)

        return etree.tostring(envi, encoding="unicode")

    def _parse_retorno(self, xml):
        root = etree.fromstring(xml)

        def find(tag):
            el = root.find(f".//{{*}}{tag}")
            return el.text if el is not None else ""

        return find("cStat"), find("xMotivo"), find("nProt"), find("nRec")

    def _processar_retorno_xml(self, xml):
        cStat, xMotivo, nProt, nRec = self._parse_retorno(xml)

        if cStat == "100":
            return {"status": "autorizado", "protocolo": nProt}

        return {
            "status": "erro",
            "codigo": cStat,
            "mensagem": xMotivo,
        }
