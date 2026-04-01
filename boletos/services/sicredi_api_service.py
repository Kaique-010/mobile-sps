import os
from typing import Optional

import requests


class SicrediAPIError(Exception):
    pass


class SicrediCobrancaService:
    """Cliente HTTP para API de Cobrança Sicredi (sandbox/produção)."""

    DEFAULT_SANDBOX_BASE_URL = "https://api-parceiro.sicredi.com.br"
    DEFAULT_PROD_BASE_URL = "https://api-parceiro.sicredi.com.br"

    def __init__(self, carteira):
        self.carteira = carteira

    def _clean(self, value: Optional[str]) -> str:
        return str(value or "").strip()

    def _base_url(self) -> str:
        configured = self._clean(getattr(self.carteira, "cart_webs_ssl_lib", ""))
        if configured and configured.startswith("http"):
            return configured.rstrip("/")

        ambiente = configured.lower()
        if ambiente in {"prod", "producao", "produção", "production"}:
            return self.DEFAULT_PROD_BASE_URL
        return self.DEFAULT_SANDBOX_BASE_URL

    def _token_url(self) -> str:
        env_override = self._clean(os.getenv("SICREDI_TOKEN_URL"))
        if env_override:
            return env_override
        return f"{self._base_url()}/auth/openapi/token"

    def _api_base(self) -> str:
        env_override = self._clean(os.getenv("SICREDI_COBRANCA_BASE_URL"))
        if env_override:
            return env_override.rstrip("/")
        return f"{self._base_url()}/cobranca/boleto/v1"

    def get_access_token(self) -> str:
        client_id = self._clean(getattr(self.carteira, "cart_webs_clie_id", ""))
        client_secret = self._clean(getattr(self.carteira, "cart_webs_clie_secr", ""))
        scope = self._clean(getattr(self.carteira, "cart_webs_scop", ""))
        user_key = self._clean(getattr(self.carteira, "cart_webs_user_key", ""))

        if not client_id or not client_secret:
            raise SicrediAPIError("Carteira sem client_id/client_secret configurados.")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        if user_key:
            headers["x-api-key"] = user_key

        payload = {
            "grant_type": "client_credentials",
        }
        if scope:
            payload["scope"] = scope

        response = requests.post(
            self._token_url(),
            data=payload,
            headers=headers,
            auth=(client_id, client_secret),
            timeout=30,
        )

        if response.status_code >= 400:
            raise SicrediAPIError(f"Falha ao obter token Sicredi: HTTP {response.status_code} - {response.text}")

        data = response.json()
        token = data.get("access_token")
        if not token:
            raise SicrediAPIError("Resposta de token sem access_token.")
        return token

    def _headers(self, token: str) -> dict:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        user_key = self._clean(getattr(self.carteira, "cart_webs_user_key", ""))
        if user_key:
            headers["x-api-key"] = user_key
        return headers

    def registrar_boleto(self, payload: dict) -> dict:
        token = self.get_access_token()
        url = f"{self._api_base()}/boletos"
        r = requests.post(url, json=payload, headers=self._headers(token), timeout=45)
        if r.status_code >= 400:
            raise SicrediAPIError(f"Falha ao registrar boleto: HTTP {r.status_code} - {r.text}")
        return r.json() if r.text else {"ok": True}

    def consultar_boleto(self, nosso_numero: str, params: Optional[dict] = None) -> dict:
        token = self.get_access_token()
        url = f"{self._api_base()}/boletos/{nosso_numero}"
        r = requests.get(url, params=params or {}, headers=self._headers(token), timeout=30)
        if r.status_code >= 400:
            raise SicrediAPIError(f"Falha ao consultar boleto: HTTP {r.status_code} - {r.text}")
        return r.json() if r.text else {}

    def baixar_boleto(self, nosso_numero: str, payload: Optional[dict] = None) -> dict:
        token = self.get_access_token()
        url = f"{self._api_base()}/boletos/{nosso_numero}/baixa"
        r = requests.patch(url, json=payload or {}, headers=self._headers(token), timeout=30)
        if r.status_code >= 400:
            raise SicrediAPIError(f"Falha ao baixar boleto: HTTP {r.status_code} - {r.text}")
        return r.json() if r.text else {"ok": True}

    def alterar_boleto(self, nosso_numero: str, payload: dict) -> dict:
        token = self.get_access_token()
        url = f"{self._api_base()}/boletos/{nosso_numero}"
        r = requests.patch(url, json=payload, headers=self._headers(token), timeout=30)
        if r.status_code >= 400:
            raise SicrediAPIError(f"Falha ao alterar boleto: HTTP {r.status_code} - {r.text}")
        return r.json() if r.text else {"ok": True}
