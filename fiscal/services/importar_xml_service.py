import base64

from django.core.exceptions import ValidationError

from fiscal.normalizers.nfe_normalizer import dumps_json, normalize_nfe_dict
from fiscal.parser.nfe_xml_parser import parse_nfe
from fiscal.repositories.nfe_repository import NFeRepository
from Licencas.models import Filiais
from Notas_Fiscais.infrastructure.certificado_loader import CertificadoLoader


class ImportarXMLService:
    def __init__(self, *, banco: str):
        self.banco = banco or "default"
        self.repo = NFeRepository(banco=self.banco)

    def importar(self, *, empresa: int, filial: int, xml: str):
        xml_str = _normalize_xml(xml)
        raw = parse_nfe(xml_str)
        normalizado = normalize_nfe_dict(raw)

        chave = normalizado.get("chave") or ""
        if not chave or len(chave) != 44:
            raise ValidationError("Chave da NF-e inválida ou não encontrada no XML.")

        tipo = normalizado.get("tipo") or ""
        tipo = str(tipo or "").strip().lower()
        if tipo not in ("entrada", "saida"):
            tipo = ""

        try:
            filial_obj = (
                Filiais.objects.using(self.banco)
                .only("empr_docu")
                .filter(empr_empr=int(empresa), empr_codi=int(filial))
                .first()
            )
        except Exception:
            filial_obj = None

        filial_doc = _only_digits(getattr(filial_obj, "empr_docu", "") or "") if filial_obj else ""
        dest_doc = _only_digits(((normalizado.get("destinatario") or {}).get("documento")) or "")
        emit_doc = _only_digits(((normalizado.get("emitente") or {}).get("documento")) or "")

        if filial_doc and dest_doc == filial_doc:
            tipo = "entrada"
        elif filial_doc and emit_doc == filial_doc:
            tipo = "saida"
        elif not tipo:
            tipo = "entrada"

        json_normalizado = dumps_json(normalizado)

        return self.repo.upsert_documento(
            empresa=empresa,
            filial=filial,
            chave=chave,
            tipo=tipo,
            xml_original=xml_str,
            json_normalizado=json_normalizado,
        )

    def importar_por_chave(self, *, empresa: int, filial: int, chave: str):
        chave_digits = _only_digits(chave)
        if not chave_digits or len(chave_digits) != 44:
            raise ValidationError("Chave de acesso inválida.")

        filial_obj = (
            Filiais.objects.using(self.banco)
            .defer("empr_cert_digi")
            .filter(empr_empr=int(empresa), empr_codi=int(filial))
            .first()
        )
        if not filial_obj:
            raise ValidationError("Filial não encontrada.")

        uf = (getattr(filial_obj, "empr_esta", "") or "").strip().lower()
        cnpj = _only_digits(getattr(filial_obj, "empr_docu", "") or "")
        if not uf:
            raise ValidationError("UF da filial (empr_esta) não informada.")
        if not cnpj or len(cnpj) != 14:
            raise ValidationError("CNPJ da filial (empr_docu) inválido.")

        ambi = str(getattr(filial_obj, "empr_ambi_nfe", "") or "1").strip()
        homologacao = ambi == "2"

        cert_path, cert_pass = CertificadoLoader(filial_obj).load()
        xml_baixado = _consultar_xml_por_chave(
            uf=uf,
            cert_path=cert_path,
            cert_pass=str(cert_pass or ""),
            cnpj=cnpj,
            chave=chave_digits,
            homologacao=homologacao,
        )
        return self.importar(empresa=empresa, filial=filial, xml=xml_baixado)


def _normalize_xml(xml: str) -> str:
    if xml is None:
        return ""
    s = xml.decode("utf-8", errors="ignore") if isinstance(xml, (bytes, bytearray)) else str(xml)
    s = s.strip()
    if not s:
        return ""
    if "<" in s and ">" in s:
        return s
    try:
        decoded = base64.b64decode(s, validate=True)
        decoded_str = decoded.decode("utf-8", errors="ignore").strip()
        return decoded_str or s
    except Exception:
        return s


def _only_digits(value) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _consultar_xml_por_chave(*, uf: str, cert_path: str, cert_pass: str, cnpj: str, chave: str, homologacao: bool) -> str:
    try:
        from pynfe.processamento.comunicacao import ComunicacaoSefaz
    except Exception:
        raise ValidationError("Dependência 'pynfe' não está instalada no servidor.")

    import base64 as _b64
    import gzip as _gzip
    import xml.etree.ElementTree as ET

    con = ComunicacaoSefaz(uf, cert_path, cert_pass, homologacao)
    resp = con.consulta_distribuicao(cnpj=cnpj, chave=chave)
    content = getattr(resp, "text", None) or getattr(resp, "content", b"")
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="ignore")

    if not content:
        raise ValidationError("SEFAZ não retornou resposta ao consultar a chave.")

    try:
        root = ET.fromstring(content)
    except Exception:
        raise ValidationError("Resposta da SEFAZ inválida ao consultar a chave.")

    cstat = ""
    xmotivo = ""
    try:
        cstat = (root.findtext(".//{*}cStat") or "").strip()
    except Exception:
        cstat = ""
    try:
        xmotivo = (root.findtext(".//{*}xMotivo") or "").strip()
    except Exception:
        xmotivo = ""

    if cstat and cstat not in ("137", "138"):
        if xmotivo:
            raise ValidationError(f"SEFAZ retornou cStat={cstat}: {xmotivo}")
        raise ValidationError(f"SEFAZ retornou cStat={cstat}.")

    doczips = root.findall(".//{*}docZip") or []
    xmls = []
    schemas = []
    for dz in doczips:
        payload = (dz.text or "").strip()
        if not payload:
            continue
        schema = (dz.attrib or {}).get("schema") or ""
        try:
            decoded = _b64.b64decode(payload)
        except Exception:
            continue
        try:
            decompressed = _gzip.decompress(decoded)
        except Exception:
            decompressed = decoded
        xml_str = decompressed.decode("utf-8", errors="ignore").strip()
        if xml_str:
            xmls.append(xml_str)
            schemas.append(schema)

    if not xmls:
        if cstat == "137":
            raise ValidationError("Nenhum documento localizado para a chave informada (cStat=137).")
        msg = "SEFAZ não retornou documentos para a chave informada."
        if cstat:
            if xmotivo:
                msg = f"{msg} cStat={cstat}: {xmotivo}"
            else:
                msg = f"{msg} cStat={cstat}."
        raise ValidationError(msg)

    for x in xmls:
        if "<nfeProc" in x or "<NFe" in x or "<procNFe" in x:
            return x

    for schema in schemas:
        if "resnfe" in str(schema or "").lower():
            raise ValidationError(
                "SEFAZ retornou apenas o resumo da NF-e (resNFe). Para obter o XML completo, normalmente é necessário manifestar a nota (Ciência/Confirmação/Operação não realizada)."
            )

    return xmls[0]
