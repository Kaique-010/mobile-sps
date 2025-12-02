# notas_fiscais/assinador_service.py

import tempfile
from pathlib import Path
from lxml import etree
from signxml import XMLSigner, methods
from cryptography.hazmat.primitives.serialization import (
    pkcs12,
    Encoding,
    PrivateFormat,
    NoEncryption,
)

from .exceptions import ErroEmissao

NFE_NS = "http://www.portalfiscal.inf.br/nfe"


class AssinadorA1Service:
    """
    Serviço para assinar XML de NF-e/NFC-e usando certificado A1 (PFX/P12).
    
    - Recebe OBRIGATORIAMENTE os bytes crús do certificado.
    - Não mexe com criptografia, quem controla isso é o caller.
    - Garante assinatura envelopada padrão SEFAZ (xmldsig).
    """

    def __init__(self, pfx_bytes: bytes, pfx_pass: str):
        if not isinstance(pfx_bytes, (bytes, bytearray)):
            raise ErroEmissao("Certificado inválido: pfx_bytes deve ser bytes puros.")

        self.pfx_bytes = pfx_bytes
        self.pfx_pass = pfx_pass

    def _extract_key_and_cert(self):
        """
        Extrai chave privada e certificado PEM do PFX carregado na memória.
        """
        try:
            password = self.pfx_pass.encode("utf-8") if self.pfx_pass else None
            key, cert, addl = pkcs12.load_key_and_certificates(self.pfx_bytes, password)
        except Exception:
            raise ErroEmissao("Falha ao carregar PFX: senha incorreta ou arquivo inválido.")

        if key is None or cert is None:
            raise ErroEmissao("Certificado A1 inválido ou incompleto.")

        # Converter key e cert para PEM (formato aceito pelo signxml)
        key_pem = key.private_bytes(
            Encoding.PEM,
            PrivateFormat.PKCS8,
            NoEncryption(),
        ).decode()

        cert_pem = cert.public_bytes(Encoding.PEM).decode()

        # Concatena cadeia de certificados se houver
        chain_pem = ""
        if addl:
            for c in addl:
                try:
                    chain_pem += c.public_bytes(Encoding.PEM).decode()
                except Exception:
                    pass

        return key_pem, cert_pem + chain_pem

    def assinar_xml(self, xml_str: str) -> str:
        """
        Assina o XML de NF-e/NFC-e, posicionando a <Signature> como irmã de <infNFe>.
        """
        # Carrega XML
        try:
            root = etree.fromstring(xml_str.encode("utf-8"))
        except Exception:
            raise ErroEmissao("XML inválido para assinatura.")

        # Localiza infNFe
        ns = {"nfe": NFE_NS}
        inf_list = root.xpath("//nfe:infNFe", namespaces=ns)

        if not inf_list:
            raise ErroEmissao("Elemento infNFe não encontrado para assinatura.")

        inf = inf_list[0]

        # Garante o atributo Id
        inf_id = inf.get("Id") or "NFeTEMP"
        inf.set("Id", inf_id)

        # Extrai key + cert PEM
        key_pem, cert_chain_pem = self._extract_key_and_cert()

        # Configura signer
        signer = XMLSigner(
            method=methods.enveloped,
            signature_algorithm="rsa-sha256",
            digest_algorithm="sha256",
            c14n_algorithm="http://www.w3.org/2001/10/xml-exc-c14n#",
        )

        # Assina
        signed_root = signer.sign(
            root,
            key=key_pem,
            cert=cert_chain_pem,
            reference_uri=f"#{inf_id}",
        )

        # Garante que a tag <Signature> esteja no nível certo
        ns_ds = {"ds": "http://www.w3.org/2000/09/xmldsig#"}
        signatures = signed_root.xpath("//ds:Signature", namespaces=ns_ds)

        if signatures:
            sig = signatures[0]
            parent = sig.getparent()

            # Normaliza: remove de infNFe se assinador colocou lá dentro
            if parent is not None and parent.tag.endswith("infNFe"):
                parent.remove(sig)
                signed_root.append(sig)

        # Retorna XML final
        return etree.tostring(
            signed_root,
            encoding="utf-8",
            pretty_print=False,
            xml_declaration=False,
        ).decode()
