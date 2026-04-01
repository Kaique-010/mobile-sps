import os
import logging
from typing import Optional

import requests


class SicrediAPIError(Exception):
    pass


logger = logging.getLogger(__name__)


class SicrediCobrancaService:
    """Cliente HTTP para API de Cobrança Sicredi (sandbox/produção)."""

    DEFAULT_SANDBOX_BASE_URL = "https://api-parceiro.sicredi.com.br"
    DEFAULT_PROD_BASE_URL = "https://api-parceiro.sicredi.com.br"
    ALT_TOKEN_PATHS = (
        "/auth/openapi/token",
        "/auth/token",
        "/oauth/token",
        "/openapi/token",
        "/openapi/oauth/token",
    )

    def __init__(self, carteira):
        self.carteira = carteira

    def _clean(self, value: Optional[str]) -> str:
        return str(value or "").strip()

    def _base_url(self) -> str:
        configured = self._clean(getattr(self.carteira, "cart_webs_ssl_lib", ""))
        if configured and configured.startswith("http"):
            return configured.rstrip("/")

        ambiente = configured.lower()
        if ambiente in {"sandbox", "homolog", "teste", "testing"}:
            return self.DEFAULT_SANDBOX_BASE_URL
        return self.DEFAULT_PROD_BASE_URL

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

    def _token_url_candidates(self):
        override = self._clean(os.getenv("SICREDI_TOKEN_URL"))
        if override:
            yield override
        base = self._base_url()
        seen = set()
        for p in self.ALT_TOKEN_PATHS:
            url = f"{base}{p}"
            if url not in seen:
                seen.add(url)
                yield url

    def _mask(self, value: str) -> str:
        v = self._clean(value)
        if not v:
            return ""
        if len(v) <= 6:
            return f"{v[:2]}***{v[-1:]}"
        return f"{v[:4]}***{v[-2:]}"

    def get_access_token(self) -> str:
        client_id = self._clean(getattr(self.carteira, "cart_webs_clie_id", ""))
        client_secret = self._clean(getattr(self.carteira, "cart_webs_clie_secr", ""))
        scope = self._clean(getattr(self.carteira, "cart_webs_scop", ""))
        user_key = self._clean(getattr(self.carteira, "cart_webs_user_key", ""))

        logger.info(
            "[sicredi] token_request carteira=(empr=%s,fili=%s,banc=%s,codi=%s,nome=%s) urls=(base=%s,token=%s,api=%s) auth=(client_id=%s,has_secret=%s,secret_len=%s) headers=(has_x_api_key=%s) scope=%s ssl_lib=%s env_overrides=(token_url=%s,api_base=%s)",
            getattr(self.carteira, "cart_empr", None),
            getattr(self.carteira, "cart_fili", None),
            getattr(self.carteira, "cart_banc", None),
            getattr(self.carteira, "cart_codi", None),
            getattr(self.carteira, "cart_nome", None),
            self._base_url(),
            self._token_url(),
            self._api_base(),
            self._mask(client_id),
            bool(client_secret),
            len(client_secret) if client_secret else 0,
            bool(user_key),
            scope or "",
            self._clean(getattr(self.carteira, "cart_webs_ssl_lib", "")),
            bool(self._clean(os.getenv("SICREDI_TOKEN_URL"))),
            bool(self._clean(os.getenv("SICREDI_COBRANCA_BASE_URL"))),
        )

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

        errors = []
        for url in self._token_url_candidates():
            try:
                response = requests.post(url, data=payload, headers=headers, auth=(client_id, client_secret), timeout=30)
            except Exception as ex:
                errors.append(f"{url} EXC {type(ex).__name__}")
                continue
            if response.status_code < 400:
                data = response.json()
                token = data.get("access_token")
                if token:
                    return token
                errors.append(f"{url} 200 sem_access_token")
                continue
            body = (response.text or "").strip()
            if len(body) > 2000:
                body = body[:2000]
            logger.warning("[sicredi] token_response_error status=%s url=%s body=%s", response.status_code, url, body)
            if response.status_code in (400, 401):
                retry_payload = dict(payload)
                retry_payload["client_id"] = client_id
                retry_payload["client_secret"] = client_secret
                try:
                    retry = requests.post(url, data=retry_payload, headers=headers, timeout=30)
                except Exception as ex:
                    errors.append(f"{url} RETRY EXC {type(ex).__name__}")
                    continue
                if retry.status_code < 400:
                    data = retry.json()
                    token = data.get("access_token")
                    if token:
                        return token
                    errors.append(f"{url} RETRY 200 sem_access_token")
                    continue
                retry_body = (retry.text or "").strip()
                if len(retry_body) > 2000:
                    retry_body = retry_body[:2000]
                logger.warning("[sicredi] token_retry_error status=%s url=%s body=%s", retry.status_code, url, retry_body)
                errors.append(f"{url} RETRY {retry.status_code}")
            else:
                errors.append(f"{url} {response.status_code}")
        raise SicrediAPIError("Falha ao obter token Sicredi: " + " | ".join(errors))

        # Unreachable

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
