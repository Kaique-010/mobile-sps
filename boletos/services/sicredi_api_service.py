import os
import logging
import base64
from typing import Optional

import requests
from .online_banks.wallet_config import validate_online_wallet_config


class SicrediAPIError(Exception):
    pass


logger = logging.getLogger(__name__)


class SicrediCobrancaService:
    """Cliente HTTP para API de Cobrança Sicredi (sandbox/produção)."""

    DEFAULT_SANDBOX_BASE_URL = "https://api-parceiro.sicredi.com.br/sb"
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

    def _normalize_nosso_numero_candidates(self, nosso_numero: str):
        raw = self._clean(nosso_numero)
        digits = "".join(ch for ch in raw if ch.isdigit())
        if not digits:
            return [raw] if raw else []
        candidates = []
        for v in (digits, digits.lstrip("0") or "0"):
            if v and v not in candidates:
                candidates.append(v)
        for size in (9, 10, 15):
            v = digits.zfill(size)
            if v not in candidates:
                candidates.append(v)
        return candidates

    def _raise_for_status(self, response: requests.Response, prefix: str):
        if response.status_code < 400:
            return
        body_full = (response.text or "").strip()
        body = body_full[:2000]
        hint = ""
        if response.status_code == 404:
            lower = body_full.lower()
            if "without destination" in lower or "found matching route" in lower:
                hint = " (API Sicredi sem destino para esta operação; normalmente indica recurso não habilitado no produto/app/convênio)"
        raise SicrediAPIError(f"{prefix}: HTTP {response.status_code} - {body}{hint}")

    def get_access_token(self) -> str:
        try:
            cfg = validate_online_wallet_config(self.carteira, "Sicredi")
        except ValueError as exc:
            raise SicrediAPIError(str(exc))
        client_id = cfg["client_id"]
        client_secret = cfg["client_secret"]
        scope = cfg["scope"]
        user_key = cfg["api_key"]

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
        posto_cfg = self._clean(getattr(self.carteira, "cart_codi_tran", ""))
        posto_cfg_digits = "".join(ch for ch in posto_cfg if ch.isdigit())
        posto = posto_cfg_digits[:2] if len(posto_cfg_digits) >= 2 else (cedente[:2] if len(cedente) >= 2 else "01")
        posto_override = self._clean(os.getenv("SICREDI_POSTO"))
        cooperativa_override = self._clean(os.getenv("SICREDI_COOPERATIVA"))
        if cooperativa_override:
            cooperativa = cooperativa_override
        if posto_override:
            posto = posto_override

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
        posto_cfg = self._clean(getattr(self.carteira, "cart_codi_tran", ""))
        posto_cfg_digits = "".join(ch for ch in posto_cfg if ch.isdigit())
        posto = posto_cfg_digits[:2] if len(posto_cfg_digits) >= 2 else (cedente[:2] if len(cedente) >= 2 else "01")
        posto_override = self._clean(os.getenv("SICREDI_POSTO"))
        cooperativa_override = self._clean(os.getenv("SICREDI_COOPERATIVA"))
        beneficiario_override = self._clean(os.getenv("SICREDI_CODIGO_BENEFICIARIO"))
        if cooperativa_override:
            cooperativa = cooperativa_override
        if posto_override:
            posto = posto_override
        if beneficiario_override:
            cedente = beneficiario_override
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
        r = requests.post(url, params=self._routing_params(), json=payload, headers=self._headers(token), timeout=45)
        self._raise_for_status(r, "Falha ao registrar boleto")
        return r.json() if r.text else {"ok": True}

    def consultar_boleto(self, nosso_numero: str, params: Optional[dict] = None) -> dict:
        token = self.get_access_token()
        merged_params = {**self._routing_params(), **(params or {})}
        errors = []

        for nn in self._normalize_nosso_numero_candidates(nosso_numero):
            url_list = f"{self._api_base()}/boletos"
            params_list = {**merged_params, "nossoNumero": nn}
            r = requests.get(url_list, params=params_list, headers=self._headers(token), timeout=30)
            if r.status_code < 400:
                data = r.json() if r.text else {}
                if isinstance(data, list) and data:
                    return data[0]
                if isinstance(data, dict) and data:
                    return data
            else:
                errors.append(f"GET /boletos?nossoNumero={nn} -> {r.status_code}")

            url_one = f"{self._api_base()}/boletos/{nn}"
            r = requests.get(url_one, params=merged_params, headers=self._headers(token), timeout=30)
            if r.status_code < 400:
                data = r.json() if r.text else {}
                if isinstance(data, list) and data:
                    return data[0]
                return data
            errors.append(f"GET /boletos/{nn} -> {r.status_code}")

        raise SicrediAPIError("Falha ao consultar boleto: " + " | ".join(errors))

    def baixar_boleto(self, nosso_numero: str, payload: Optional[dict] = None) -> dict:
        token = self.get_access_token()
        return self._baixar_boleto_com_token(token, nosso_numero, payload=payload)

    def _baixar_boleto_com_token(self, token: str, nosso_numero: str, payload: Optional[dict] = None) -> dict:
        params = self._routing_params()
        errors = []

        for nn in self._normalize_nosso_numero_candidates(nosso_numero):
            url1 = f"{self._api_base()}/boletos/{nn}/baixa"
            r = requests.patch(url1, params=params, json=payload or {}, headers=self._headers(token), timeout=30)
            if r.status_code < 400:
                return r.json() if r.text else {"ok": True}
            errors.append(f"PATCH /boletos/{nn}/baixa -> {r.status_code} {(r.text or '').strip()[:200]}")

            r = requests.post(url1, params=params, json=payload or {}, headers=self._headers(token), timeout=30)
            if r.status_code < 400:
                return r.json() if r.text else {"ok": True}
            errors.append(f"POST /boletos/{nn}/baixa -> {r.status_code} {(r.text or '').strip()[:200]}")

            url1b = f"{self._api_base()}/boletos/{nn}/pedido-baixa"
            r = requests.patch(url1b, params=params, json=payload or {}, headers=self._headers(token), timeout=30)
            if r.status_code < 400:
                return r.json() if r.text else {"ok": True}
            errors.append(f"PATCH /boletos/{nn}/pedido-baixa -> {r.status_code} {(r.text or '').strip()[:200]}")

            url2 = f"{self._api_base()}/boletos/baixa"
            params2 = {**params, "nossoNumero": nn}
            r = requests.patch(url2, params=params2, json=payload or {}, headers=self._headers(token), timeout=30)
            if r.status_code < 400:
                return r.json() if r.text else {"ok": True}
            errors.append(f"PATCH /boletos/baixa?nossoNumero={nn} -> {r.status_code} {(r.text or '').strip()[:200]}")

            r = requests.post(url2, params=params2, json=payload or {}, headers=self._headers(token), timeout=30)
            if r.status_code < 400:
                return r.json() if r.text else {"ok": True}
            errors.append(f"POST /boletos/baixa?nossoNumero={nn} -> {r.status_code} {(r.text or '').strip()[:200]}")

        raise SicrediAPIError("Falha ao baixar boleto: " + " | ".join(errors))

    def alterar_boleto(self, nosso_numero: str, payload: dict) -> dict:
        token = self.get_access_token()
        params = self._routing_params()
        errors = []
        normalized_payload = dict(payload or {})
        if "dataVencimento" not in normalized_payload:
            if normalized_payload.get("novoVencimento"):
                normalized_payload["dataVencimento"] = normalized_payload["novoVencimento"]
            elif normalized_payload.get("vencimento"):
                normalized_payload["dataVencimento"] = normalized_payload["vencimento"]

        for nn in self._normalize_nosso_numero_candidates(nosso_numero):
            url_v = f"{self._api_base()}/boletos/{nn}/vencimento"
            r = requests.patch(url_v, params=params, json=normalized_payload, headers=self._headers(token), timeout=30)
            if r.status_code < 400:
                return r.json() if r.text else {"ok": True}
            errors.append(f"PATCH /boletos/{nn}/vencimento -> {r.status_code} {(r.text or '').strip()[:200]}")

            r = requests.put(url_v, params=params, json=normalized_payload, headers=self._headers(token), timeout=30)
            if r.status_code < 400:
                return r.json() if r.text else {"ok": True}
            errors.append(f"PUT /boletos/{nn}/vencimento -> {r.status_code} {(r.text or '').strip()[:200]}")
            url_v2 = f"{self._api_base()}/boletos/{nn}/alterar-vencimento"
            r = requests.patch(url_v2, params=params, json=normalized_payload, headers=self._headers(token), timeout=30)
            if r.status_code < 400:
                return r.json() if r.text else {"ok": True}
            errors.append(f"PATCH /boletos/{nn}/alterar-vencimento -> {r.status_code} {(r.text or '').strip()[:200]}")

            url1 = f"{self._api_base()}/boletos/{nn}"
            r = requests.patch(url1, params=params, json=normalized_payload, headers=self._headers(token), timeout=30)
            if r.status_code < 400:
                return r.json() if r.text else {"ok": True}
            errors.append(f"PATCH /boletos/{nn} -> {r.status_code} {(r.text or '').strip()[:200]}")

            url2 = f"{self._api_base()}/boletos"
            params2 = {**params, "nossoNumero": nn}
            r = requests.patch(url2, params=params2, json=normalized_payload, headers=self._headers(token), timeout=30)
            if r.status_code < 400:
                return r.json() if r.text else {"ok": True}
            errors.append(f"PATCH /boletos?nossoNumero={nn} -> {r.status_code} {(r.text or '').strip()[:200]}")

            r = requests.put(url1, params=params, json=normalized_payload, headers=self._headers(token), timeout=30)
            if r.status_code < 400:
                return r.json() if r.text else {"ok": True}
            errors.append(f"PUT /boletos/{nn} -> {r.status_code} {(r.text or '').strip()[:200]}")

            url2b = f"{self._api_base()}/boletos/vencimento"
            r = requests.patch(url2b, params=params2, json=normalized_payload, headers=self._headers(token), timeout=30)
            if r.status_code < 400:
                return r.json() if r.text else {"ok": True}
            errors.append(f"PATCH /boletos/vencimento?nossoNumero={nn} -> {r.status_code} {(r.text or '').strip()[:200]}")

            r = requests.put(url2b, params=params2, json=normalized_payload, headers=self._headers(token), timeout=30)
            if r.status_code < 400:
                return r.json() if r.text else {"ok": True}
            errors.append(f"PUT /boletos/vencimento?nossoNumero={nn} -> {r.status_code} {(r.text or '').strip()[:200]}")

        raise SicrediAPIError("Falha ao alterar boleto: " + " | ".join(errors))

    def cancelar_boleto(self, nosso_numero: str, payload: Optional[dict] = None) -> dict:
        token = self.get_access_token()
        params = self._routing_params()
        errors = []

        for nn in self._normalize_nosso_numero_candidates(nosso_numero):
            url1 = f"{self._api_base()}/boletos/{nn}/cancelamento"
            r = requests.patch(url1, params=params, json=payload or {}, headers=self._headers(token), timeout=30)
            if r.status_code < 400:
                return r.json() if r.text else {"ok": True}
            errors.append(f"PATCH /boletos/{nn}/cancelamento -> {r.status_code} {(r.text or '').strip()[:200]}")

            r = requests.post(url1, params=params, json=payload or {}, headers=self._headers(token), timeout=30)
            if r.status_code < 400:
                return r.json() if r.text else {"ok": True}
            errors.append(f"POST /boletos/{nn}/cancelamento -> {r.status_code} {(r.text or '').strip()[:200]}")

            url1b = f"{self._api_base()}/boletos/{nn}/cancelar"
            r = requests.patch(url1b, params=params, json=payload or {}, headers=self._headers(token), timeout=30)
            if r.status_code < 400:
                return r.json() if r.text else {"ok": True}
            errors.append(f"PATCH /boletos/{nn}/cancelar -> {r.status_code} {(r.text or '').strip()[:200]}")

            if r.status_code in (404, 405):
                try:
                    return self._baixar_boleto_com_token(token, nn, payload=payload)
                except SicrediAPIError as ex:
                    errors.append(f"PATCH /boletos/{nn}/cancelamento -> {r.status_code} baixa_falhou")
                    errors.append(str(ex)[:200])
                    continue

        raise SicrediAPIError("Falha ao cancelar boleto: " + " | ".join(errors))

    def obter_pdf_boleto(self, nosso_numero: str, linha_digitavel: Optional[str] = None) -> bytes:
        token = self.get_access_token()
        headers = dict(self._headers(token))
        headers["Accept"] = "application/pdf"
        params_base = self._routing_params()

        ld = self._clean(linha_digitavel)
        ld_digits = "".join(ch for ch in ld if ch.isdigit())

        candidates = []
        for nn in self._normalize_nosso_numero_candidates(nosso_numero):
            candidates.append((f"{self._api_base()}/boletos/{nn}/pdf", params_base))
            candidates.append((f"{self._api_base()}/boletos/{nn}/impressao", params_base))
            candidates.append((f"{self._api_base()}/boletos/pdf", {**params_base, "nossoNumero": nn}))
            candidates.append((f"{self._api_base()}/boletos/impressao", {**params_base, "nossoNumero": nn}))

        if ld_digits:
            candidates.append((f"{self._api_base()}/boletos/pdf", {**params_base, "linhaDigitavel": ld_digits}))
            candidates.append((f"{self._api_base()}/boletos/impressao", {**params_base, "linhaDigitavel": ld_digits}))

        errors = []
        for url, params in candidates:
            try:
                r = requests.get(url, params=params, headers=headers, timeout=45)
            except Exception as ex:
                errors.append(f"GET {url} EXC {type(ex).__name__}")
                continue

            if r.status_code >= 400:
                errors.append(f"GET {url} -> {r.status_code}")
                continue

            content = r.content or b""
            if content.startswith(b"%PDF"):
                return content

            ct = (r.headers.get("Content-Type") or "").lower()
            if "application/pdf" in ct and content:
                return content

            try:
                data = r.json() if (r.text or "").strip() else {}
            except Exception:
                data = {}

            if isinstance(data, dict):
                b64 = data.get("pdf") or data.get("conteudoPdf") or data.get("conteudoPDF")
                if b64 and isinstance(b64, str):
                    try:
                        decoded = base64.b64decode(b64, validate=False)
                    except Exception:
                        decoded = b""
                    if decoded.startswith(b"%PDF"):
                        return decoded

                link = data.get("linkBoleto") or data.get("urlBoleto") or data.get("boletoUrl")
                if link and isinstance(link, str) and link.startswith("http"):
                    r2 = requests.get(link, headers={"Accept": "application/pdf"}, timeout=45)
                    if r2.status_code < 400 and (r2.content or b"").startswith(b"%PDF"):
                        return r2.content
                    errors.append(f"GET {link} -> {r2.status_code}")
                    continue

        raise SicrediAPIError("Falha ao obter PDF do boleto: " + " | ".join(errors))
