import os
import requests
from .wallet_config import validate_online_wallet_config


class OnlineBankAPIError(Exception):
    pass


class BaseOAuthBoletoService:
    """Base hexagonal para APIs de boleto com OAuth client_credentials."""

    bank_code = None
    bank_name = None

    def __init__(self, carteira):
        self.carteira = carteira

    def _clean(self, value):
        return str(value or '').strip()

    def _env(self, name):
        return self._clean(os.getenv(name))

    def _base_url(self):
        configured = self._clean(getattr(self.carteira, 'cart_webs_ssl_lib', ''))
        if configured.startswith('http'):
            return configured.rstrip('/')
        env_base = self._env(f'{self.bank_code}_BASE_URL')
        if env_base:
            return env_base.rstrip('/')
        raise OnlineBankAPIError(f'URL base não configurada para {self.bank_name}.')

    def token_url(self):
        custom = self._env(f'{self.bank_code}_TOKEN_URL')
        if custom:
            return custom
        return f'{self._base_url()}{self.default_token_path()}'

    def boletos_url(self):
        custom = self._env(f'{self.bank_code}_BOLETOS_URL')
        if custom:
            return custom.rstrip('/')
        return f'{self._base_url()}{self.default_boletos_path()}'

    def default_token_path(self):
        raise NotImplementedError

    def default_boletos_path(self):
        raise NotImplementedError

    def _token(self):
        try:
            cfg = validate_online_wallet_config(self.carteira, self.bank_name)
        except ValueError as exc:
            raise OnlineBankAPIError(str(exc))
        client_id = cfg['client_id']
        client_secret = cfg['client_secret']
        scope = cfg['scope']
        api_key = cfg['api_key']

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        if api_key:
            headers['x-api-key'] = api_key

        data = {'grant_type': 'client_credentials'}
        if scope:
            data['scope'] = scope

        r = requests.post(self.token_url(), data=data, headers=headers, auth=(client_id, client_secret), timeout=30)
        if r.status_code >= 400:
            raise OnlineBankAPIError(f'Erro ao obter token {self.bank_name}: HTTP {r.status_code} - {r.text}')

        token = (r.json() or {}).get('access_token')
        if not token:
            raise OnlineBankAPIError(f'Resposta sem access_token ({self.bank_name}).')
        return token

    def _headers(self, token):
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        api_key = self._clean(getattr(self.carteira, 'cart_webs_user_key', ''))
        if api_key:
            headers['x-api-key'] = api_key
        return headers

    def registrar_boleto(self, payload):
        token = self._token()
        r = requests.post(self.boletos_url(), json=payload, headers=self._headers(token), timeout=45)
        if r.status_code >= 400:
            raise OnlineBankAPIError(f'Erro ao registrar boleto ({self.bank_name}): HTTP {r.status_code} - {r.text}')
        return r.json() if r.text else {'ok': True}

    def consultar_boleto(self, nosso_numero):
        token = self._token()
        r = requests.get(f"{self.boletos_url()}/{nosso_numero}", headers=self._headers(token), timeout=30)
        if r.status_code >= 400:
            raise OnlineBankAPIError(f'Erro ao consultar boleto ({self.bank_name}): HTTP {r.status_code} - {r.text}')
        return r.json() if r.text else {}

    def baixar_boleto(self, nosso_numero, payload=None):
        token = self._token()
        return self._baixar_boleto_com_token(token, nosso_numero, payload=payload)

    def _baixar_boleto_com_token(self, token, nosso_numero, payload=None):
        r = requests.patch(f"{self.boletos_url()}/{nosso_numero}/baixa", json=payload or {}, headers=self._headers(token), timeout=30)
        if r.status_code >= 400:
            raise OnlineBankAPIError(f'Erro ao baixar boleto ({self.bank_name}): HTTP {r.status_code} - {r.text}')
        return r.json() if r.text else {'ok': True}

    def cancelar_boleto(self, nosso_numero, payload=None):
        """
        Padrão multi-banco:
        - tenta endpoint explícito de cancelamento
        - fallback para baixa para manter compatibilidade
        """
        token = self._token()
        cancel_url = f"{self.boletos_url()}/{nosso_numero}/cancelamento"
        r = requests.patch(cancel_url, json=payload or {}, headers=self._headers(token), timeout=30)
        if r.status_code in (404, 405):
            return self._baixar_boleto_com_token(token, nosso_numero, payload=payload)
        if r.status_code >= 400:
            raise OnlineBankAPIError(f'Erro ao cancelar boleto ({self.bank_name}): HTTP {r.status_code} - {r.text}')
        return r.json() if r.text else {'ok': True}

    def alterar_boleto(self, nosso_numero, payload):
        token = self._token()
        r = requests.patch(f"{self.boletos_url()}/{nosso_numero}", json=payload, headers=self._headers(token), timeout=30)
        if r.status_code >= 400:
            raise OnlineBankAPIError(f'Erro ao alterar boleto ({self.bank_name}): HTTP {r.status_code} - {r.text}')
        return r.json() if r.text else {'ok': True}
