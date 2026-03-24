import tempfile
import logging
from Licencas.crypto import decrypt_bytes, decrypt_str
import os
from Licencas.models import Filiais


logger = logging.getLogger(__name__)


class CertificadoLoader:
    """     
    Carrega o certificado digital da filial.
    Usa os campos:
    - empr_cert_digi (bytes)
    - empr_senh_cert
    """

    def __init__(self, filial):
        self.filial = filial

    def load(self):
        cert_token = None
        senha_token = getattr(self.filial, "empr_senh_cert", None)
        caminho_arquivo = getattr(self.filial, "empr_cert", None)
        db_alias = getattr(getattr(self.filial, "_state", None), "db", None) or "default"

        empr_empr = getattr(self.filial, "empr_empr", None)
        empr_codi = getattr(self.filial, "empr_codi", None)
        if empr_empr is not None and empr_codi is not None:
            try:
                row = (
                    Filiais.objects.using(db_alias)
                    .filter(empr_empr=empr_empr, empr_codi=empr_codi)
                    .values_list("empr_cert_digi", "empr_senh_cert", "empr_cert")
                    .first()
                )
                if row:
                    cert_token, senha_token, caminho_arquivo = row
            except Exception:
                cert_token = None

        # Se não encontrou no banco, tenta via arquivo (fallback legado)
        if not cert_token:
            if caminho_arquivo:
                if os.path.isfile(caminho_arquivo):
                    try:
                        senha = decrypt_str(senha_token)
                    except Exception:
                        senha = senha_token
                    return caminho_arquivo, (senha or "")
            env_path = os.environ.get("CTE_PFX_PATH") or os.environ.get("PFX_PATH")
            env_pass = os.environ.get("CTE_PFX_PASSWORD") or os.environ.get("PFX_PASSWORD")
            if env_path and os.path.isfile(env_path):
                logger.info("Usando certificado A1 via ambiente: %s", env_path)
                return env_path, (env_pass or "")

        if not cert_token:
            raise Exception("Filial não possui certificado digital cadastrado (nem banco, nem arquivo).")

        try:
            senha = decrypt_str(senha_token)
        except Exception:
            senha = senha_token

        if senha is None:
            senha = ""

        logger.info("Carregando certificado digital para filial %s", getattr(self.filial, "id", None))

        try:
            cert_bytes = decrypt_bytes(cert_token)
        except Exception as e:
            logger.error(f"Falha ao descriptografar certificado da filial {getattr(self.filial, 'id', 'N/A')}: {e}")
            cert_bytes = cert_token
            if hasattr(cert_bytes, "tobytes"):
                cert_bytes = cert_bytes.tobytes()
            elif isinstance(cert_bytes, str):
                logger.warning("Certificado em formato string e falhou na descriptografia. Tentando converter para bytes.")
                cert_bytes = cert_bytes.encode('utf-8')

        if not isinstance(cert_bytes, (bytes, bytearray)):
            raise TypeError(f"Conteúdo do certificado não é bytes. Tipo atual: {type(cert_bytes)}")

        f = tempfile.NamedTemporaryFile(delete=False, suffix=".pfx")
        f.write(cert_bytes)
        f.flush()

        logger.info("Certificado temporário criado: %s", f.name)

        return f.name, senha
