import logging
from lxml import etree
from signxml import XMLSigner, methods
from cryptography.hazmat.primitives.serialization import (
    pkcs12,
    Encoding,
    PrivateFormat,
    NoEncryption,
)

from transportes.models import Cte
from Licencas.models import Filiais
from Notas_Fiscais.infrastructure.certificado_loader import CertificadoLoader

logger = logging.getLogger(__name__)

CTE_NS = "http://www.portalfiscal.inf.br/cte"

class AssinaturaService:
    def __init__(self, cte: Cte):
        self.cte = cte
        self.filial = None
        self._carregar_filial()

    def _carregar_filial(self):
        try:
            # Garante o uso do mesmo banco de dados do CTe (multi-tenancy)
            db_alias = self.cte._state.db or 'default'
            
            self.filial = Filiais.objects.using(db_alias).defer('empr_cert_digi').filter(
                empr_empr=self.cte.empresa,
                empr_codi=self.cte.filial
            ).first()
            if not self.filial:
                 raise Exception("Filial não encontrada.")
        except Exception as e:
            logger.error(f"Erro ao carregar dados da filial para assinatura: {e}")
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
                xml = xml[idx + 2:].strip()

        return xml.strip()

    def assinar(self, xml_content: str) -> str:
        """Assina o XML do CTe usando o certificado digital da filial"""
        
        caminho_certificado = None
        senha_certificado = None

        try:
            # Usa o CertificadoLoader para descriptografar e salvar temporariamente o certificado
            caminho_certificado, senha_certificado = CertificadoLoader(self.filial).load()
        except Exception as e:
            raise Exception(f"Certificado digital não configurado/indisponível: {str(e)}")

        if not caminho_certificado:
            raise Exception("Certificado digital não configurado/indisponível.")

        try:
            with open(caminho_certificado, "rb") as f:
                pfx_bytes = f.read()

            password = (senha_certificado or "").encode("utf-8") if senha_certificado else None
            key, cert, addl = pkcs12.load_key_and_certificates(pfx_bytes, password)

            if key is None or cert is None:
                raise Exception("Certificado A1 inválido ou incompleto.")

            key_pem = key.private_bytes(
                Encoding.PEM,
                PrivateFormat.PKCS8,
                NoEncryption(),
            ).decode("utf-8")

            cert_pem = cert.public_bytes(Encoding.PEM).decode("utf-8")
            if addl:
                for c in addl:
                    try:
                        cert_pem += c.public_bytes(Encoding.PEM).decode("utf-8")
                    except Exception:
                        pass

            xml_content = self._normalizar_xml(xml_content)
            parser = etree.XMLParser(resolve_entities=False, no_network=True, recover=False)
            root = etree.fromstring(xml_content.encode("utf-8"), parser=parser)
            if etree.QName(root).localname != "CTe" or etree.QName(root).namespace != CTE_NS:
                raise Exception("XML inválido: raiz deve ser <CTe> no namespace do CT-e.")
            ns = {"cte": CTE_NS}
            inf_list = root.xpath("//cte:infCte", namespaces=ns)
            if not inf_list:
                raise Exception("Elemento infCte não encontrado para assinatura.")

            inf = inf_list[0]
            inf_id = (inf.get("Id") or "").strip() or "CTeTEMP"
            inf.set("Id", inf_id)

            signer = XMLSigner(
                method=methods.enveloped,
                signature_algorithm="rsa-sha256",
                digest_algorithm="sha256",
                c14n_algorithm="http://www.w3.org/2001/10/xml-exc-c14n#",
            )

            signed_root = signer.sign(
                root,
                key=key_pem,
                cert=cert_pem,
                reference_uri=f"#{inf_id}",
            )

            ns_ds = {"ds": "http://www.w3.org/2000/09/xmldsig#"}
            signatures = signed_root.xpath("//ds:Signature", namespaces=ns_ds)
            if signatures:
                sig = signatures[0]
                parent = sig.getparent()
                if parent is not None and parent.tag.endswith("infCte"):
                    parent.remove(sig)
                    signed_root.append(sig)

            return etree.tostring(
                signed_root,
                encoding="utf-8",
                pretty_print=False,
                xml_declaration=False,
            ).decode("utf-8")
        except Exception as e:
            logger.error(f"Erro ao assinar XML: {e}")
            raise Exception(f"Falha na assinatura digital: {str(e)}")
