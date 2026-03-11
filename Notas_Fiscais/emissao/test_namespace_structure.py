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
if _root not in sys.path:
    sys.path.insert(0, _root)
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
            r'<ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#"\1',
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
        "chave": "00000000000000000000000000000000000000000000",
        "cNF": "12345678",
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
            "cUF": "41",
            "logradouro": "Rua",
            "numero": "1",
            "bairro": "Centro",
            "cod_municipio": "4119905",
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
            "cod_municipio": "4119905",
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
                "cst_icms": "00",
                "cst_pis": "01",
                "cst_cofins": "01",
                "unidade": "PCT",
                "quantidade": 1,
                "valor_unit": 100.0,
                "desconto": 0.0,
            }
        ],
        "tpag": "01",
    }

def test_normalizar_serie_ide():
    from Notas_Fiscais.infrastructure.sefaz_adapter import SefazAdapter
    xml = "<NFe xmlns='http://www.portalfiscal.inf.br/nfe'><infNFe><ide><serie>005</serie></ide></infNFe></NFe>"
    root = etree.fromstring(xml.encode("utf-8"))
    adapter = SefazAdapter.__new__(SefazAdapter)
    adapter._normalizar_serie_ide(root)
    ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
    assert root.findtext(".//nfe:ide/nfe:serie", namespaces=ns) == "5"

def test_csrt_sem_id_nao_injeta_hash():
    from Notas_Fiscais.infrastructure.sefaz_adapter import SefazAdapter

    class RespTec:
        cnpj = "20702018000142"
        contato = "TESTE"
        email = "teste@teste.com"
        fone = "41999999999"
        id_csrt = None
        csrt_key = "CHAVE_FAKE"
        hash_csrt = None

    xml = "<NFe xmlns='http://www.portalfiscal.inf.br/nfe'><infNFe Id='NFe00000000000000000000000000000000000000000000'></infNFe></NFe>"
    root = etree.fromstring(xml.encode("utf-8"))
    adapter = SefazAdapter.__new__(SefazAdapter)
    adapter._injetar_responsavel_tecnico(root, RespTec())
    out = etree.tostring(root, encoding="unicode")
    assert "<hashCSRT>" not in out

def test_csrt_com_id_injeta_hash():
    from Notas_Fiscais.infrastructure.sefaz_adapter import SefazAdapter

    class RespTec:
        cnpj = "20702018000142"
        contato = "TESTE"
        email = "teste@teste.com"
        fone = "41999999999"
        id_csrt = "1"
        csrt_key = "CHAVE_FAKE"
        hash_csrt = None

    xml = "<NFe xmlns='http://www.portalfiscal.inf.br/nfe'><infNFe Id='NFe00000000000000000000000000000000000000000000'></infNFe></NFe>"
    root = etree.fromstring(xml.encode("utf-8"))
    adapter = SefazAdapter.__new__(SefazAdapter)
    adapter._injetar_responsavel_tecnico(root, RespTec())
    out = etree.tostring(root, encoding="unicode")
    assert "<idCSRT>" in out
    assert "<hashCSRT>" in out
    assert out.index("<idCSRT>") < out.index("<hashCSRT>")
    assert "<idCSRT>01</idCSRT>" in out

def test_csrt_limpa_infresptec_invalido_existente():
    from Notas_Fiscais.infrastructure.sefaz_adapter import SefazAdapter

    class RespTec:
        cnpj = "20702018000142"
        contato = "TESTE"
        email = "teste@teste.com"
        fone = "41999999999"
        id_csrt = "1"
        csrt_key = "CHAVE_FAKE"
        hash_csrt = None

    xml = (
        "<NFe xmlns='http://www.portalfiscal.inf.br/nfe'>"
        "<infNFe Id='NFe00000000000000000000000000000000000000000000'>"
        "<infRespTec><hashCSRT>AAA</hashCSRT></infRespTec>"
        "</infNFe>"
        "</NFe>"
    )
    root = etree.fromstring(xml.encode("utf-8"))
    adapter = SefazAdapter.__new__(SefazAdapter)
    adapter._injetar_responsavel_tecnico(root, RespTec())
    out = etree.tostring(root, encoding="unicode")
    assert out.count("<infRespTec>") == 1
    assert out.index("<idCSRT>") < out.index("<hashCSRT>")
    assert "<idCSRT>01</idCSRT>" in out

def test_parse_envio_autorizacao_nfeproc():
    from Notas_Fiscais.infrastructure.sefaz_adapter import SefazAdapter

    xml = (
        "<nfeProc xmlns='http://www.portalfiscal.inf.br/nfe' versao='4.00'>"
        "<NFe><infNFe Id='NFe41260362377583000121550050000000031532212883'/></NFe>"
        "<protNFe><infProt>"
        "<tpAmb>2</tpAmb>"
        "<verAplic>PR-v4_9_69</verAplic>"
        "<chNFe>41260362377583000121550050000000031532212883</chNFe>"
        "<dhRecbto>2026-03-11T15:45:18-03:00</dhRecbto>"
        "<nProt>141260000000000</nProt>"
        "<digVal>AAA=</digVal>"
        "<cStat>100</cStat>"
        "<xMotivo>Autorizado o uso da NF-e</xMotivo>"
        "</infProt></protNFe>"
        "</nfeProc>"
    )
    root = etree.fromstring(xml.encode("utf-8"))
    adapter = SefazAdapter.__new__(SefazAdapter)
    status, motivo, protocolo, chave, xml_protocolo = adapter._parse_envio_autorizacao((0, root))
    assert status == 100
    assert protocolo == "141260000000000"
    assert chave == "41260362377583000121550050000000031532212883"
    assert "protNFe" in (xml_protocolo or "")


def main():
    test_normalizar_serie_ide()
    test_csrt_sem_id_nao_injeta_hash()
    test_csrt_com_id_injeta_hash()
    test_csrt_limpa_infresptec_invalido_existente()
    test_parse_envio_autorizacao_nfeproc()
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
