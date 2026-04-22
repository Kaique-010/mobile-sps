class NfseError(Exception):
    """Erro base do módulo de NFS-e."""


class NfseClientError(NfseError):
    def __init__(
        self,
        message: str,
        *,
        payload: dict | None = None,
        xml_envio: str | None = None,
        xml_retorno: str | None = None,
        resposta: dict | None = None,
        status_code: int | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.payload = payload
        self.xml_envio = xml_envio
        self.xml_retorno = xml_retorno
        self.resposta = resposta
        self.status_code = status_code

    def __str__(self):
        return self.message


class NfseSoapError(NfseClientError):
    """Erro retornado pelo serviço SOAP."""


class NfseHttpError(NfseClientError):
    """Erro de transporte HTTP."""


class NfseParseError(NfseClientError):
    """Erro ao interpretar XML de retorno."""