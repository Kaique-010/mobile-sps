from datetime import datetime

import os
import requests

from .base import OnlineBankAPIError
from .wallet_config import validate_online_wallet_config


class BancoBrasilAPIError(OnlineBankAPIError):
    pass


class BancoBrasilCobrancaService:
    bank_code = "BB"
    bank_name = "Banco do Brasil"

    DEFAULT_BASE_PROD = "https://api.bb.com.br/cobrancas/v2"
    DEFAULT_BASE_HM = "https://api.hm.bb.com.br/cobrancas/v2"
    DEFAULT_BASE_SANDBOX = "https://api.sandbox.bb.com.br/cobrancas/v2"

    DEFAULT_OAUTH_PROD = "https://oauth.bb.com.br/oauth/token"
    DEFAULT_OAUTH_HM = "https://oauth.hm.bb.com.br/oauth/token"
    DEFAULT_OAUTH_SANDBOX = "https://oauth.sandbox.bb.com.br/oauth/token"
    REQUIRED_ALTERAR_INDICADORES = (
        "indicadorAlterarAbatimento",
        "indicadorAlterarDataDesconto",
        "indicadorAlterarDesconto",
        "indicadorAlterarEnderecoPagador",
        "indicadorAlterarPrazoBoletoVencido",
        "indicadorAlterarSeuNumero",
        "indicadorAtribuirDesconto",
        "indicadorCancelarProtesto",
        "indicadorCobrarJuros",
        "indicadorCobrarMulta",
        "indicadorDispensarJuros",
        "indicadorDispensarMulta",
        "indicadorIncluirAbatimento",
        "indicadorNegativar",
        "indicadorNovaDataVencimento",
        "indicadorProtestar",
        "indicadorSustacaoProtesto",
        "indicadorNovoValorNominal",
    )

    def __init__(self, carteira):
        self.carteira = carteira
        self.cfg = validate_online_wallet_config(carteira, bank_name=self.bank_name)

    def _clean(self, value):
        return str(value or "").strip()

    def _base_url(self):
        base = self._clean(self.cfg.get("base"))
        if base.startswith("http"):
            return base.rstrip("/")
        ambiente = base.lower()
        if ambiente in {"sandbox"}:
            return self.DEFAULT_BASE_SANDBOX
        if ambiente in {"homolog", "hm", "teste", "testing"}:
            return self.DEFAULT_BASE_HM
        return self.DEFAULT_BASE_PROD

    def _token_url(self):
        override = self._clean(os.getenv("BB_TOKEN_URL"))
        if override:
            return override
        base = self._base_url()
        if "sandbox.bb.com.br" in base:
            return self.DEFAULT_OAUTH_SANDBOX
        if "hm.bb.com.br" in base:
            return self.DEFAULT_OAUTH_HM
        return self.DEFAULT_OAUTH_PROD

    def _numero_convenio(self):
        raw = self._clean(getattr(self.carteira, "cart_conv", ""))
        digits = "".join(ch for ch in raw if ch.isdigit())
        return digits
    
    def _digits(self, value):
        return "".join(ch for ch in self._clean(value) if ch.isdigit())

    def _id_candidates(self, nosso_numero):
        raw = self._clean(nosso_numero)
        digits = self._digits(raw)
        seen = set()

        if digits:
            if digits not in seen:
                seen.add(digits)
                yield digits

        convenio = self._numero_convenio()
        if not convenio:
            return

        conv7 = self._digits(convenio)
        if len(conv7) > 7:
            conv7 = conv7[-7:]
        conv7 = conv7.zfill(7)

        nn_inputs = []
        if digits:
            nn_inputs.append(digits)
            nn_inputs.append(digits.lstrip("0"))
        else:
            nn_inputs.append(raw)

        for nn in nn_inputs:
            nn_digits = self._digits(nn)
            if not nn_digits:
                continue
            if len(nn_digits) > 10:
                nn10 = nn_digits[-10:]
            else:
                nn10 = nn_digits.zfill(10)
            bb_id = f"000{conv7}{nn10}"
            if bb_id not in seen:
                seen.add(bb_id)
                yield bb_id

    def _app_key(self):
        return self._clean(self.cfg.get("api_key"))

    def _app_params(self):
        app_key = self._app_key()
        if not app_key:
            raise BancoBrasilAPIError("Carteira sem gw-dev-app-key configurada.")
        return {"gw-dev-app-key": app_key, "gw-app-key": app_key}

    def _token(self):
        client_id = self._clean(self.cfg.get("client_id"))
        client_secret = self._clean(self.cfg.get("client_secret"))
        scope = self._clean(self.cfg.get("scope"))
        if not client_id or not client_secret:
            raise BancoBrasilAPIError("Carteira sem client_id/client_secret configurados.")
        data = {"grant_type": "client_credentials"}
        if scope:
            data["scope"] = scope
        r = requests.post(
            self._token_url(),
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            auth=(client_id, client_secret),
            timeout=30,
        )
        if r.status_code >= 400:
            raise BancoBrasilAPIError(f"Erro ao obter token {self.bank_name}: HTTP {r.status_code} - {r.text}")
        token = (r.json() or {}).get("access_token")
        if not token:
            raise BancoBrasilAPIError(f"Resposta sem access_token ({self.bank_name}).")
        return token

    def _headers(self, token):
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def _request(self, method, url, *, params=None, headers=None, json=None, timeout=30):
        try:
            return requests.request(method, url, params=params, headers=headers, json=json, timeout=timeout)
        except Exception as ex:
            raise BancoBrasilAPIError(f"Falha na requisição {self.bank_name}: {type(ex).__name__}")

    def registrar_boleto(self, payload):
        token = self._token()
        url = f"{self._base_url()}/boletos"
        r = self._request("POST", url, params=self._app_params(), json=payload, headers=self._headers(token), timeout=45)
        if r.status_code >= 400:
            raise BancoBrasilAPIError(f"Erro ao registrar boleto ({self.bank_name}): HTTP {r.status_code} - {r.text}")
        return r.json() if r.text else {"ok": True}

    def consultar_boleto(self, nosso_numero):
        token = self._token()
        convenio = self._numero_convenio()
        if not convenio:
            raise BancoBrasilAPIError("Carteira sem número de convênio (cart_conv) configurado.")
        params = {**self._app_params(), "numeroConvenio": convenio}
        errors = []
        for bb_id in self._id_candidates(nosso_numero):
            url = f"{self._base_url()}/boletos/{bb_id}"
            r = self._request("GET", url, params=params, headers=self._headers(token), timeout=30)
            if r.status_code == 404:
                errors.append(f"GET /boletos/{bb_id} -> 404")
                continue
            if r.status_code >= 400:
                raise BancoBrasilAPIError(f"Erro ao consultar boleto ({self.bank_name}): HTTP {r.status_code} - {r.text}")
            return r.json() if r.text else {}
        raise BancoBrasilAPIError(f"Boleto não encontrado no {self.bank_name}. Tentativas: {', '.join(errors) or 'sem_candidatos'}")

    def baixar_boleto(self, nosso_numero, payload=None):
        token = self._token()
        convenio = self._numero_convenio()
        if not convenio:
            raise BancoBrasilAPIError("Carteira sem número de convênio (cart_conv) configurado.")
        body = {"numeroConvenio": convenio}
        if isinstance(payload, dict):
            body.update(payload)
        errors = []
        for bb_id in self._id_candidates(nosso_numero):
            url = f"{self._base_url()}/boletos/{bb_id}/baixar"
            r = self._request("POST", url, params=self._app_params(), json=body, headers=self._headers(token), timeout=30)
            if r.status_code == 404:
                errors.append(f"POST /boletos/{bb_id}/baixar -> 404")
                continue
            if r.status_code >= 400:
                raise BancoBrasilAPIError(f"Erro ao baixar/cancelar boleto ({self.bank_name}): HTTP {r.status_code} - {r.text}")
            return r.json() if r.text else {"ok": True}
        raise BancoBrasilAPIError(f"Não foi possível baixar/cancelar no {self.bank_name}. Tentativas: {', '.join(errors) or 'sem_candidatos'}")

    def cancelar_boleto(self, nosso_numero, payload=None):
        return self.baixar_boleto(nosso_numero, payload=payload)

    def alterar_boleto(self, nosso_numero, payload):
        token = self._token()
        convenio = self._numero_convenio()
        if not convenio:
            raise BancoBrasilAPIError("Carteira sem número de convênio (cart_conv) configurado.")
        data = payload if isinstance(payload, dict) else {}

        if "dataVencimento" in data and "alteracaoData" not in data and "indicadorNovaDataVencimento" not in data:
            raw = self._clean(data.get("dataVencimento"))
            try:
                dt = datetime.fromisoformat(raw[:10])
                bb_date = dt.strftime("%d.%m.%Y")
            except Exception:
                bb_date = ""
            if not bb_date:
                raise BancoBrasilAPIError("Data de vencimento inválida para alteração no BB.")
            base = {k: "N" for k in self.REQUIRED_ALTERAR_INDICADORES}
            base.update(
                {
                    "numeroConvenio": int(convenio) if convenio.isdigit() else convenio,
                    "indicadorNovaDataVencimento": "S",
                    "alteracaoData": {"novaDataVencimento": bb_date},
                }
            )
            data = base
        else:
            base = {k: "N" for k in self.REQUIRED_ALTERAR_INDICADORES}
            merged = dict(data)
            for k in self.REQUIRED_ALTERAR_INDICADORES:
                if k in merged and self._clean(merged.get(k)).upper() in {"S", "N"}:
                    base[k] = self._clean(merged.get(k)).upper()
            if "alteracaoData" in merged:
                base["alteracaoData"] = merged.get("alteracaoData")
            if "alteracaoValor" in merged:
                base["alteracaoValor"] = merged.get("alteracaoValor")
            if "alteracaoDesconto" in merged:
                base["alteracaoDesconto"] = merged.get("alteracaoDesconto")
            if "alteracaoDataDesconto" in merged:
                base["alteracaoDataDesconto"] = merged.get("alteracaoDataDesconto")
            if "alteracaoPrazo" in merged:
                base["alteracaoPrazo"] = merged.get("alteracaoPrazo")
            if "alteracaoSeuNumero" in merged:
                base["alteracaoSeuNumero"] = merged.get("alteracaoSeuNumero")
            if "alteracaoEndereco" in merged:
                base["alteracaoEndereco"] = merged.get("alteracaoEndereco")
            if "juros" in merged:
                base["juros"] = merged.get("juros")
            if "multa" in merged:
                base["multa"] = merged.get("multa")
            if "abatimento" in merged:
                base["abatimento"] = merged.get("abatimento")
            if "alteracaoAbatimento" in merged:
                base["alteracaoAbatimento"] = merged.get("alteracaoAbatimento")
            if "negativacao" in merged:
                base["negativacao"] = merged.get("negativacao")
            if "protesto" in merged:
                base["protesto"] = merged.get("protesto")
            base["numeroConvenio"] = int(convenio) if convenio.isdigit() else convenio
            data = base

        errors = []
        for bb_id in self._id_candidates(nosso_numero):
            url = f"{self._base_url()}/boletos/{bb_id}"
            r = self._request("PATCH", url, params=self._app_params(), json=data, headers=self._headers(token), timeout=30)
            if r.status_code == 404:
                errors.append(f"PATCH /boletos/{bb_id} -> 404")
                continue
            if r.status_code >= 400:
                raise BancoBrasilAPIError(f"Erro ao alterar boleto ({self.bank_name}): HTTP {r.status_code} - {r.text}")
            return r.json() if r.text else {"ok": True}
        raise BancoBrasilAPIError(f"Não foi possível alterar no {self.bank_name}. Tentativas: {', '.join(errors) or 'sem_candidatos'}")
