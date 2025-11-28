import tempfile


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
        if not self.filial.empr_cert_digi:
            raise Exception("Filial não possui certificado digital cadastrado.")

        senha = self.filial.empr_senh_cert
        bytes_cert = self.filial.empr_cert_digi

        f = tempfile.NamedTemporaryFile(delete=False, suffix=".pfx")
        f.write(bytes_cert)
        f.flush()

        return f.name, senha
