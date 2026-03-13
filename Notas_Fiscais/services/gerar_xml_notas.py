import io
import logging
from pathlib import Path
import zipfile

from django.core.mail import EmailMessage

from Notas_Fiscais.models import Nota
from core.utils import get_db_from_slug

logger = logging.getLogger(__name__)

STATUS_EXPORTAR = [100, 101, 102, 301, 302]


def pasta_status(status):
    mapa = {
        100: "autorizadas",
        101: "canceladas",
        102: "inutilizadas",
        301: "denegadas",
        302: "denegadas",
    }
    return mapa.get(status, "outros")


def _nome_xml_nota(nota: Nota) -> str:
    chave = str((nota.chave_acesso or "")).strip()
    base = chave or f"{nota.modelo}_{nota.serie}_{nota.numero}_{nota.id}"
    return f"{base}.xml"


def _obter_xml_nota(nota: Nota) -> str | None:
    xml = (getattr(nota, "xml_autorizado", None) or "").strip()
    if xml:
        return xml
    try:
        xml = nota.gerar_xml()
    except Exception:
        return None
    xml = (xml or "").strip()
    return xml or None


def gerar_xml_notas(notas, base_path="xml", salvar_em_disco=True):
    gerados = []
    for nota in notas:
        xml = _obter_xml_nota(nota)
        if not xml:
            logger.warning("Nota %s sem XML para exportação", getattr(nota, "id", None))
            continue

        nome = _nome_xml_nota(nota)
        relpath = Path(str(nota.empresa)) / pasta_status(nota.status) / nome

        if salvar_em_disco:
            pasta = Path(base_path) / relpath.parent
            pasta.mkdir(parents=True, exist_ok=True)
            arquivo = pasta / nome
            arquivo.write_text(xml, encoding="utf-8")
            gerados.append(str(arquivo))
        else:
            gerados.append(str(relpath))

    return gerados


def gerar_zip_xml_notas(notas, *, incluir_pastas=True) -> tuple[bytes, dict]:
    arquivos = []
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for nota in notas:
            xml = _obter_xml_nota(nota)
            if not xml:
                logger.warning("Nota %s sem XML para exportação", getattr(nota, "id", None))
                continue

            nome = _nome_xml_nota(nota)
            if incluir_pastas:
                arq_zip = str(Path(str(nota.empresa)) / pasta_status(nota.status) / nome).replace("\\", "/")
            else:
                arq_zip = nome

            zf.writestr(arq_zip, xml)
            arquivos.append(arq_zip)

    payload = buf.getvalue()
    return payload, {"quantidade": len(arquivos), "arquivos": arquivos}


def enviar_zip_contabilidade(*, destinatarios: list[str], zip_bytes: bytes, nome_arquivo: str, assunto: str, mensagem: str):
    destinatarios = [e.strip() for e in (destinatarios or []) if str(e or "").strip()]
    if not destinatarios:
        raise ValueError("Destinatários não informados")

    email = EmailMessage(subject=assunto, body=mensagem, to=destinatarios)
    email.attach(nome_arquivo, zip_bytes, "application/zip")
    email.send(fail_silently=False)


def gerar_e_enviar_xml_contabilidade(
    *,
    empresa: int,
    filial: int,
    periodo,
    slug: str | None = None,
    destinatarios: list[str] | None = None,
    incluir_pastas: bool = True,
    status_list: list[int] | None = None,
):
    banco = get_db_from_slug(slug) if slug else "default"
    status_list = status_list or STATUS_EXPORTAR

    notas = (
        Nota.objects.using(banco)
        .filter(
            empresa=empresa,
            filial=filial,
            data_emissao__range=periodo,
            status__in=status_list,
        )
        .only("id", "empresa", "filial", "modelo", "serie", "numero", "status", "chave_acesso", "xml_autorizado")
        .order_by("data_emissao", "numero")
    )

    zip_bytes, info = gerar_zip_xml_notas(notas, incluir_pastas=incluir_pastas)

    ini, fim = periodo
    nome_zip = f"xml_notas_{empresa}_{filial}_{ini}_{fim}.zip"
    assunto = f"XML Notas Fiscais {empresa}/{filial} - {ini} a {fim}"
    mensagem = f"Segue em anexo o arquivo ZIP com {info['quantidade']} XML(s) do período {ini} a {fim}."

    enviar_zip_contabilidade(
        destinatarios=destinatarios or [],
        zip_bytes=zip_bytes,
        nome_arquivo=nome_zip,
        assunto=assunto,
        mensagem=mensagem,
    )

    return {"banco": banco, "empresa": empresa, "filial": filial, "periodo": [str(ini), str(fim)], **info, "nome_zip": nome_zip}
