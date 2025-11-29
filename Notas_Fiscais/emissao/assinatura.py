import tempfile
from pathlib import Path
from .exceptions import ErroEmissao
from lxml import etree
from signxml import XMLSigner, methods
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption

class AssinadorA1Service:
    def __init__(self, pfx_path, pfx_pass):
        self.pfx_path = pfx_path
        self.pfx_pass = pfx_pass

    def _extract_keys(self):
        try:
            data = Path(self.pfx_path).read_bytes()
        except FileNotFoundError:
            raise ErroEmissao("Arquivo de certificado (.pfx) não encontrado.")

        try:
            key, cert, addl = pkcs12.load_key_and_certificates(
                data,
                (self.pfx_pass or "").encode("utf-8") if self.pfx_pass is not None else None,
            )
        except Exception:
            raise ErroEmissao("Falha ao carregar PFX: senha inválida ou arquivo corrompido.")

        tempdir = tempfile.mkdtemp()
        key_path = Path(tempdir) / "key.pem"
        cert_path = Path(tempdir) / "cert.pem"

        key_pem = key.private_bytes(
            Encoding.PEM,
            PrivateFormat.TraditionalOpenSSL,
            NoEncryption(),
        )
        cert_pem = cert.public_bytes(Encoding.PEM)
        chain_pem = b""
        if addl:
            for c in addl:
                try:
                    chain_pem += c.public_bytes(Encoding.PEM)
                except Exception:
                    pass

        key_path.write_bytes(key_pem)
        cert_path.write_bytes(cert_pem + chain_pem)

        return str(cert_path), str(key_path)

    def assinar_xml(self, xml_str):
        try:
            data = Path(self.pfx_path).read_bytes()
        except FileNotFoundError:
            raise ErroEmissao("Arquivo de certificado (.pfx) não encontrado.")

        try:
            key, cert, _ = pkcs12.load_key_and_certificates(
                data,
                (self.pfx_pass or "").encode("utf-8") if self.pfx_pass is not None else None,
            )
        except Exception:
            raise ErroEmissao("Falha ao carregar PFX: senha inválida ou arquivo corrompido.")

        key_pem = key.private_bytes(
            Encoding.PEM,
            PrivateFormat.PKCS8,
            NoEncryption(),
        ).decode("utf-8")
        cert_pem = cert.public_bytes(Encoding.PEM).decode("utf-8")

        try:
            root = etree.fromstring(xml_str.encode("utf-8"))
        except Exception:
            raise ErroEmissao("XML inválido para assinatura.")

        ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
        inf_list = root.xpath("//nfe:infNFe", namespaces=ns)
        if not inf_list:
            raise ErroEmissao("Elemento infNFe não encontrado para assinatura.")
        inf = inf_list[0]

        inf_id = inf.get("Id") or "NFeTEMP"
        if not inf.get("Id"):
            inf.set("Id", inf_id)

        signer = XMLSigner(
            method=methods.enveloped,
            signature_algorithm="rsa-sha256",
            digest_algorithm="sha256",
            c14n_algorithm="http://www.w3.org/2001/10/xml-exc-c14n#",
        )

        signed_inf = signer.sign(
            inf,
            key=key_pem,
            cert=cert_pem,
            reference_uri=f"#{inf_id}",
        )
        parent = inf.getparent()
        if parent is not None:
            parent.replace(inf, signed_inf)
        else:
            raise ErroEmissao("Estrutura XML inválida: infNFe sem elemento pai.")

        return etree.tostring(root, encoding="utf-8", pretty_print=False, xml_declaration=False).decode("utf-8")
