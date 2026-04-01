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

        if not client_id or not client_secret:
            raise SicrediAPIError("Carteira sem client_id/client_secret configurados.")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "context": "COBRANCA",  # <-- ESSE ERA O PROBLEMA
        }
        if user_key:
            headers["x-api-key"] = user_key

        payload = {
            "grant_type": "password",  # <-- E ESSE TAMBÉM, MUDA DE client_credentials PRA password
            "username": client_id,
            "password": client_secret,
        }
        if scope:
            payload["scope"] = scope

        errors = []
        for url in self._token_url_candidates():
            try:
                response = requests.post(url, data=payload, headers=headers, timeout=30)
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
            body = (response.text or "").strip()[:2000]
            logger.warning("[sicredi] token_response_error status=%s url=%s body=%s", response.status_code, url, body)
            errors.append(f"{url} {response.status_code}")

        raise SicrediAPIError("Falha ao obter token Sicredi: " + " | ".join(errors))

        # Unreachable

    def _headers(self, token: str) -> dict:
        client_id = self._clean(getattr(self.carteira, "cart_webs_clie_id", ""))
        # username = beneficiario(5) + cooperativa(4) = 9 dígitos
        cooperativa = client_id[-4:] if len(client_id) >= 4 else client_id
        # posto vem do cart_codi_cede (ex: "04271") -> 2 primeiros dígitos
        cedente = self._clean(getattr(self.carteira, "cart_codi_cede", ""))
        posto = cedente[:2] if len(cedente) >= 2 else "01"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "context": "COBRANCA",
            "cooperativa": cooperativa,
            "posto": posto,
        }
        user_key = self._clean(getattr(self.carteira, "cart_webs_user_key", ""))
        if user_key:
            headers["x-api-key"] = user_key
        return headers

    def _routing_params(self) -> dict:
        client_id = self._clean(getattr(self.carteira, "cart_webs_clie_id", ""))
        cooperativa = client_id[-4:] if len(client_id) >= 4 else client_id
        cedente = self._clean(getattr(self.carteira, "cart_codi_cede", ""))
        posto = cedente[:2] if len(cedente) >= 2 else "01"
        params = {
            "cooperativa": cooperativa,
            "posto": posto,
        }
        if cedente:
            params["codigoBeneficiario"] = cedente
        return params


    def _cooperativa(self) -> str:
        """Extrai os últimos 4 dígitos do client_id (username = beneficiario + cooperativa)."""
        client_id = self._clean(getattr(self.carteira, "cart_webs_clie_id", ""))
        return client_id[-4:] if len(client_id) >= 4 else client_id
    
    def _posto(self) -> str:
        """Extrai os últimos 4 dígitos do client_id (username = beneficiario + posto)."""
        client_id = self._clean(getattr(self.carteira, "cart_webs_clie_id", ""))
        return client_id[-4:] if len(client_id) >= 4 else client_id
    
    
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
        merged_params = {**self._routing_params(), **(params or {})}
        r = requests.get(url, params=merged_params, headers=self._headers(token), timeout=30)
        if r.status_code == 404 and "without destination" in (r.text or "").lower():
            url2 = f"{self._api_base()}/boletos"
            params2 = {**merged_params, "nossoNumero": nosso_numero}
            r = requests.get(url2, params=params2, headers=self._headers(token), timeout=30)
        if r.status_code >= 400:
            raise SicrediAPIError(f"Falha ao consultar boleto: HTTP {r.status_code} - {r.text}")
        data = r.json() if r.text else {}
        if isinstance(data, list) and data:
            return data[0]
        return data

    def baixar_boleto(self, nosso_numero: str, payload: Optional[dict] = None) -> dict:
        token = self.get_access_token()
        url = f"{self._api_base()}/boletos/{nosso_numero}/baixa"
        params = self._routing_params()
        r = requests.patch(url, params=params, json=payload or {}, headers=self._headers(token), timeout=30)
        if r.status_code == 404 and "without destination" in (r.text or "").lower():
            url2 = f"{self._api_base()}/boletos/baixa"
            params2 = {**params, "nossoNumero": nosso_numero}
            r = requests.patch(url2, params=params2, json=payload or {}, headers=self._headers(token), timeout=30)
        if r.status_code >= 400:
            raise SicrediAPIError(f"Falha ao baixar boleto: HTTP {r.status_code} - {r.text}")
        return r.json() if r.text else {"ok": True}

    def alterar_boleto(self, nosso_numero: str, payload: dict) -> dict:
        token = self.get_access_token()
        url = f"{self._api_base()}/boletos/{nosso_numero}"
        params = self._routing_params()
        r = requests.patch(url, params=params, json=payload, headers=self._headers(token), timeout=30)
        if r.status_code == 404 and "without destination" in (r.text or "").lower():
            url2 = f"{self._api_base()}/boletos"
            params2 = {**params, "nossoNumero": nosso_numero}
            r = requests.patch(url2, params=params2, json=payload, headers=self._headers(token), timeout=30)
        if r.status_code in (404, 405) and "without destination" in (r.text or "").lower():
            r = requests.put(url, params=params, json=payload, headers=self._headers(token), timeout=30)
        if r.status_code >= 400:
            raise SicrediAPIError(f"Falha ao alterar boleto: HTTP {r.status_code} - {r.text}")
        return r.json() if r.text else {"ok": True}
