import requests

from nfse.exceptions import NfseHttpError


class HttpClient:
    def __init__(self, timeout: int = 60):
        self.timeout = timeout

    def post(self, *, url: str, data: str, headers: dict | None = None, auth=None, cert=None, verify=True):
        try:
            response = requests.post(
                url=url,
                data=data.encode('utf-8') if isinstance(data, str) else data,
                headers=headers or {},
                timeout=self.timeout,
                auth=auth,
                cert=cert,
                verify=verify,
            )
            response.raise_for_status()
            return response

        except requests.HTTPError as exc:
            response = exc.response
            raise NfseHttpError(
                f'Erro HTTP ao consumir serviço NFS-e: {response.status_code}',
                xml_envio=data if isinstance(data, str) else None,
                xml_retorno=response.text if response is not None else None,
                status_code=response.status_code if response is not None else None,
                resposta={
                    'url': url,
                    'status_code': response.status_code if response is not None else None,
                    'response_text': response.text if response is not None else None,
                },
            ) from exc

        except requests.RequestException as exc:
            raise NfseHttpError(
                f'Erro de comunicação com serviço NFS-e: {exc}',
                xml_envio=data if isinstance(data, str) else None,
                resposta={'url': url},
            ) from exc