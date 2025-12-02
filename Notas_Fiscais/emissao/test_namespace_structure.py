from lxml import etree
from signxml import XMLSigner, methods
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
from cryptography import x509
from cryptography.x509.oid import NameOID
from datetime import datetime, timedelta
import os
import sys

import importlib.util

def _import_from_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_root = os.getcwd()
_gerador = _import_from_path("gerador_xml", os.path.join(_root, "Notas_Fiscais", "emissao", "gerador_xml.py"))
GeradorXML = _gerador.GeradorXML

def montar_envi_nfe(xml_assinado: str, id_lote: str) -> str:
    NFE_NS = "http://www.portalfiscal.inf.br/nfe"
    id_lote_fmt = (id_lote or "1").zfill(15)
    import re
    # garantir xmlns:ds no elemento Signature
    if "<ds:Signature" in xml_assinado and "xmlns:ds=\"http://www.w3.org/2000/09/xmldsig#\"" not in xml_assinado:
        xml_assinado = re.sub(
            r"<ds:Signature(\s|>)",
            r"<ds:Signature xmlns:ds=\"http://www.w3.org/2000/09/xmldsig#\" ",
            xml_assinado,
            count=1,
        )
    # garantir xmlns padrão na tag NFe
    if not re.search(r"<NFe[^>]*\sxmlns=([\"'])http://www\\.portalfiscal\\.inf\\.br/nfe\1", xml_assinado):
        xml_assinado = re.sub(
            r"<NFe(\s[^>]*)?>",
            r"<NFe\1 xmlns=\"http://www.portalfiscal.inf.br/nfe\">",
            xml_assinado,
            count=1,
        )
    # remover xmlns:ds da tag NFe
    xml_assinado = re.sub(
        r"(<NFe[^>]*?)\sxmlns:ds=([\"'])http://www\.w3\.org/2000/09/xmldsig#\2",
        r"\1",
        xml_assinado,
    )
    return (
        f'<enviNFe xmlns="{NFE_NS}" versao="4.00">'
        f'<idLote>{id_lote_fmt}</idLote>'
        f'<indSinc>1</indSinc>'
        f'{xml_assinado}'
        f'</enviNFe>'
    )


def _gen_key_cert():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Teste"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Teste Cert"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    key_pem = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode("utf-8")
    cert_pem = cert.public_bytes(Encoding.PEM).decode("utf-8")
    return key_pem, cert_pem


def build_dto():
    return {
        "modelo": 55,
        "serie": 1,
        "numero": 1,
        "tipo_operacao": 1,
        "ambiente": 2,
        "finalidade": 1,
        "emitente": {
            "cnpj": "00000000000191",
            "razao": "Empresa Teste",
            "ie": "1234567890",
            "logradouro": "Rua",
            "numero": "1",
            "bairro": "Centro",
            "cod_municipio": 4119905,
            "municipio": "Ponta Grossa",
            "uf": "PR",
            "cep": "84015265",
        },
        "destinatario": {
            "documento": "00000000000",
            "nome": "Cliente",
            "logradouro": "Rua",
            "numero": "2",
            "bairro": "Bairro",
            "cod_municipio": 4119905,
            "municipio": "PONTA GROSSA",
            "uf": "PR",
            "cep": "84026020",
        },
        "itens": [
            {
                "codigo": "1",
                "descricao": "Item",
                "ncm": "85176239",
                "cfop": "5102",
                "unidade": "PCT",
                "quantidade": 1,
                "valor_unit": 100.0,
                "desconto": 0.0,
            }
        ],
        "tpag": "01",
    }


def main():
    dto = build_dto()
    xml = GeradorXML().gerar(dto)
    root = etree.fromstring(xml.encode("utf-8"))
    ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
    assert root.tag.endswith("NFe"), "Raiz deve ser NFe"
    assert root.nsmap.get(None) == "http://www.portalfiscal.inf.br/nfe", "Namespace padrão ausente em NFe"

    inf = root.xpath("//nfe:infNFe", namespaces=ns)[0]
    inf_id = inf.get("Id") or "NFeTEMP"
    if not inf.get("Id"):
        inf.set("Id", inf_id)

    key_pem, cert_pem = _gen_key_cert()
    signer = XMLSigner(
        method=methods.enveloped,
        signature_algorithm="rsa-sha256",
        digest_algorithm="sha256",
        c14n_algorithm="http://www.w3.org/2001/10/xml-exc-c14n#",
    )
    signed = signer.sign(root, key=key_pem, cert=cert_pem, reference_uri=f"#{inf_id}")
    sroot = etree.fromstring(etree.tostring(signed))
    nsds = {"ds": "http://www.w3.org/2000/09/xmldsig#"}
    sig_parent = sroot.xpath('//ds:Signature/..', namespaces=nsds)
    assert sig_parent and sig_parent[0].tag.endswith("NFe"), "Signature deve ser filho de NFe (irmão de infNFe)"

    xml_envi = montar_envi_nfe(etree.tostring(signed).decode("utf-8"), id_lote="1")
    eroot = etree.fromstring(xml_envi.encode("utf-8"))
    assert eroot.tag.endswith("enviNFe")
    assert eroot.nsmap.get(None) == "http://www.portalfiscal.inf.br/nfe", "Namespace padrão ausente em enviNFe"
    nfe_child = eroot.xpath("//nfe:NFe", namespaces=ns)
    assert nfe_child, "NFe deve existir dentro de enviNFe e herdar o namespace padrão"
    assert "<NFe xmlns=\"http://www.portalfiscal.inf.br/nfe\"" in xml_envi, "NFe deve declarar o xmlns padrão para evitar 587"
    # validar que NFe não tem xmlns:ds e que ds:Signature declara seu próprio prefixo
    assert "xmlns:ds=\"http://www.w3.org/2000/09/xmldsig#\"" not in xml_envi.split("<NFe")[1].split(">")[0], "NFe não deve declarar xmlns:ds"
    assert "<ds:Signature xmlns:ds=\"http://www.w3.org/2000/09/xmldsig#\"" in xml_envi, "Signature deve declarar xmlns:ds no próprio elemento"

    print("OK: Estrutura e namespaces válidos para NF-e e enviNFe")


if __name__ == "__main__":
    main()
