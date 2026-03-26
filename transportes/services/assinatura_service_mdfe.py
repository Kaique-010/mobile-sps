import logging
import hashlib
import base64
from lxml import etree
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding

from transportes.models import Mdfe
from Licencas.models import Filiais
from Notas_Fiscais.infrastructure.certificado_loader import CertificadoLoader

logger = logging.getLogger(__name__)

MDFE_NS = "http://www.portalfiscal.inf.br/mdfe"
DSIG_NS = "http://www.w3.org/2000/09/xmldsig#"
C14N_ALG = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
ENVELOPED_ALG = "http://www.w3.org/2000/09/xmldsig#enveloped-signature"
RSA_SHA1_ALG = "http://www.w3.org/2000/09/xmldsig#rsa-sha1"
SHA1_ALG = "http://www.w3.org/2000/09/xmldsig#sha1"


class AssinaturaMDFeService:
    def __init__(self, mdfe: Mdfe):
        self.mdfe = mdfe
        self.filial = None
        self._carregar_filial()

    def _carregar_filial(self):
        db_alias = self.mdfe._state.db or "default"
        self.filial = (
            Filiais.objects.using(db_alias)
            .defer("empr_cert_digi")
            .filter(empr_empr=self.mdfe.mdf_empr, empr_codi=self.mdfe.mdf_fili)
            .first()
        )
        if not self.filial:
            raise Exception("Dados da filial emitente não encontrados.")

    def _normalizar_xml(self, xml_str: str) -> str:
        xml = (xml_str or "").strip()
        xml = xml.lstrip("\ufeff\r\n\t ")
        if (xml.startswith('"') and xml.endswith('"')) or (xml.startswith("'") and xml.endswith("'")):
            xml = xml[1:-1].strip()
        while xml[:9].lower() == "undefined":
            xml = xml[9:].lstrip()
        while xml[-9:].lower() == "undefined":
            xml = xml[:-9].rstrip()
        if xml.startswith("<?xml"):
            idx = xml.find("?>")
            if idx != -1:
                xml = xml[idx + 2 :].strip()
        return xml.strip()

    def _c14n_elemento(self, element, ns_uri: str) -> bytes:
        xml_str = etree.tostring(element, encoding="unicode")
        if f'xmlns="{ns_uri}"' not in xml_str and f"xmlns='{ns_uri}'" not in xml_str:
            primeiro = min((xml_str.index(c) for c in [" ", ">", "/"] if c in xml_str), default=len(xml_str))
            xml_str = xml_str[:primeiro] + f' xmlns="{ns_uri}"' + xml_str[primeiro:]
        el = etree.fromstring(xml_str.encode("utf-8"))
        return etree.tostring(el, method="c14n", exclusive=False, with_comments=False)

    def _sha1_b64(self, data: bytes) -> str:
        return base64.b64encode(hashlib.sha1(data).digest()).decode()

    def _rsa_sha1_sign(self, data: bytes, private_key) -> str:
        signature = private_key.sign(data, padding.PKCS1v15(), hashes.SHA1())
        return base64.b64encode(signature).decode()

    def _cert_der_b64(self, cert) -> str:
        der = cert.public_bytes(Encoding.DER)
        b64 = base64.b64encode(der).decode()
        return "\n".join(b64[i : i + 76] for i in range(0, len(b64), 76))

    def assinar(self, xml_content: str) -> str:
        caminho_certificado, senha_certificado = CertificadoLoader(self.filial).load()
        if not caminho_certificado:
            raise Exception("Certificado digital não configurado/indisponível.")

        with open(caminho_certificado, "rb") as f:
            pfx_bytes = f.read()

        password = (senha_certificado or "").encode("utf-8") if senha_certificado else None
        private_key, cert, _chain = pkcs12.load_key_and_certificates(pfx_bytes, password)
        if private_key is None or cert is None:
            raise Exception("Certificado A1 inválido ou incompleto.")

        xml_content = self._normalizar_xml(xml_content)
        parser = etree.XMLParser(resolve_entities=False, no_network=True, recover=False)
        root = etree.fromstring(xml_content.encode("utf-8"), parser=parser)

        if etree.QName(root).localname != "MDFe" or etree.QName(root).namespace != MDFE_NS:
            raise Exception("XML inválido: raiz deve ser <MDFe> no namespace do MDFe.")

        ns = {"mdfe": MDFE_NS}
        inf_list = root.xpath("//mdfe:infMDFe", namespaces=ns)
        if not inf_list:
            raise Exception("Elemento infMDFe não encontrado para assinatura.")

        inf = inf_list[0]
        inf_id = (inf.get("Id") or "").strip()
        if not inf_id:
            raise Exception("infMDFe sem atributo Id.")

        inf_c14n = self._c14n_elemento(inf, MDFE_NS)
        digest_value = self._sha1_b64(inf_c14n)

        signed_info_xml = (
            f'<SignedInfo xmlns="{DSIG_NS}">'
            f'<CanonicalizationMethod Algorithm="{C14N_ALG}"></CanonicalizationMethod>'
            f'<SignatureMethod Algorithm="{RSA_SHA1_ALG}"></SignatureMethod>'
            f'<Reference URI="#{inf_id}">'
            f"<Transforms>"
            f'<Transform Algorithm="{ENVELOPED_ALG}"></Transform>'
            f'<Transform Algorithm="{C14N_ALG}"></Transform>'
            f"</Transforms>"
            f'<DigestMethod Algorithm="{SHA1_ALG}"></DigestMethod>'
            f"<DigestValue>{digest_value}</DigestValue>"
            f"</Reference>"
            f"</SignedInfo>"
        )

        signed_info_el = etree.fromstring(signed_info_xml.encode("utf-8"))
        signed_info_c14n = self._c14n_elemento(signed_info_el, DSIG_NS)
        signature_value = self._rsa_sha1_sign(signed_info_c14n, private_key)

        cert_b64 = self._cert_der_b64(cert)
        signature_xml = (
            f'<Signature xmlns="{DSIG_NS}">'
            f"{signed_info_xml}"
            f"<SignatureValue>{signature_value}</SignatureValue>"
            f"<KeyInfo>"
            f"<X509Data>"
            f"<X509Certificate>{cert_b64}</X509Certificate>"
            f"</X509Data>"
            f"</KeyInfo>"
            f"</Signature>"
        )

        sig_el = etree.fromstring(signature_xml.encode("utf-8"))
        root.append(sig_el)

        return etree.tostring(
            root,
            encoding="utf-8",
            pretty_print=False,
            xml_declaration=False,
        ).decode("utf-8")
