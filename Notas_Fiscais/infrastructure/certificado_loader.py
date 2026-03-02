import tempfile
import logging
from Licencas.crypto import decrypt_bytes, decrypt_str


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
        try:
            # Tenta acessar o campo binário (pode falhar se a coluna não existir no DB)
            if hasattr(self.filial, 'empr_cert_digi'):
                cert_token = self.filial.empr_cert_digi
        except Exception:
            pass

        # Se não encontrou no banco, tenta via arquivo (fallback legado)
        if not cert_token:
            caminho_arquivo = getattr(self.filial, 'empr_cert', None)
            if caminho_arquivo:
                import os
                if os.path.isfile(caminho_arquivo):
                    senha_token = self.filial.empr_senh_cert
                    try:
                        senha = decrypt_str(senha_token)
                    except Exception:
                        senha = senha_token
                    return caminho_arquivo, (senha or "")

        if not cert_token:
            raise Exception("Filial não possui certificado digital cadastrado (nem banco, nem arquivo).")

        senha_token = self.filial.empr_senh_cert

        try:
            senha = decrypt_str(senha_token)
        except Exception:
            senha = senha_token

        if senha is None:
            senha = ""

        logger.info("Carregando certificado digital para filial %s", getattr(self.filial, "id", None))

        try:
            cert_bytes = decrypt_bytes(cert_token)
        except Exception:
            cert_bytes = cert_token
            if hasattr(cert_bytes, "tobytes"):
                cert_bytes = cert_bytes.tobytes()

        if not isinstance(cert_bytes, (bytes, bytearray)):
            raise TypeError(f"Conteúdo do certificado não é bytes. Tipo atual: {type(cert_bytes)}")

        f = tempfile.NamedTemporaryFile(delete=False, suffix=".pfx")
        f.write(cert_bytes)
        f.flush()

        logger.info("Certificado temporário criado: %s", f.name)

        return f.name, senha
