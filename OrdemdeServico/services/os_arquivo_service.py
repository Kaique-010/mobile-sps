# services/os_arquivo_service.py
import base64
import uuid
import hashlib
from ..models import Osarquivos
from ..utils import get_next_sequential_id


class OsArquivoService:

    @staticmethod
    def _parse_base64(base64_str):
        try:
            texto = (base64_str or "").strip()
            ext = None
            if ";base64," in texto:
                header, file_str = texto.split(";base64,", 1)
                mime = header.split(":")[1]  # application/pdf
                ext = mime.split("/")[-1]
            else:
                file_str = texto.split(",", 1)[1] if "," in texto else texto

            binary = base64.b64decode(file_str)
            file_hash = hashlib.sha256(binary).hexdigest()
            return binary, ext, file_hash
        except Exception:
            raise ValueError("Base64 inválido")

    @staticmethod
    def salvar_um(os_nume, base64_str, user, empresa, filial, nome=None, banco="default"):
        binary, ext, _file_hash = OsArquivoService._parse_base64(base64_str)
        if not nome:
            nome = f"{uuid.uuid4()}.{ext}" if ext else f"{uuid.uuid4()}"

        prox_id = get_next_sequential_id(
            banco=banco,
            model=Osarquivos,
            ordem_id=os_nume,
            empresa_id=empresa,
            filial_id=filial,
            id_field="arqu_codi_arqu",
            ordem_field="arqu_os",
            empresa_field="arqu_empr",
            filial_field="arqu_fili",
        )

        obj = Osarquivos.objects.using(banco).create(
            arqu_empr=empresa,
            arqu_fili=filial,
            arqu_os=os_nume,
            arqu_codi_arqu=prox_id,
            arqu_arqu=binary,
            arqu_nome_arqu=nome,
            arqu_usua=user,
        )
        return obj

    @staticmethod
    def salvar_multiplos(os_nume, arquivos, user, empresa, filial, banco="default"):
        objs = []
        for item in arquivos:
            base64_str = item.get("base64")
            nome = item.get("nome")

            obj = OsArquivoService.salvar_um(
                os_nume, base64_str, user, empresa, filial, nome, banco=banco
            )
            if obj:
                objs.append(obj)

        return objs

    @staticmethod
    def preview(obj):
        try:
            content = getattr(obj, "arqu_arqu", None)
            if not content:
                return b""
            return bytes(content)[:200]
        except Exception:
            return "Erro ao ler"
