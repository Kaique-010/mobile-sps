import uuid

import requests

from .base import BaseOAuthBoletoService, OnlineBankAPIError


class CoraCobrancaService(BaseOAuthBoletoService):
    bank_code = 'CORA'
    bank_name = 'Cora'

    def default_token_path(self):
        return '/oauth/token'

    def default_boletos_path(self):
        return '/v2/invoices'

    def _uuid(self):
        return str(uuid.uuid4())

    def _headers(self, token):
        headers = super()._headers(token)
        headers['Accept'] = 'application/json'
        return headers

    def _normalize_response(self, data):
        data = data if isinstance(data, dict) else {}
        payment_options = data.get('payment_options') if isinstance(data.get('payment_options'), dict) else {}
        bank_slip = payment_options.get('bank_slip') if isinstance(payment_options.get('bank_slip'), dict) else {}
        pix = payment_options.get('pix') if isinstance(payment_options.get('pix'), dict) else {}

        normalized = dict(data)
        normalized.setdefault('nossoNumero', data.get('id'))
        normalized.setdefault('invoiceId', data.get('id'))
        normalized.setdefault('linhaDigitavel', bank_slip.get('digitable'))
        normalized.setdefault('linkBoleto', bank_slip.get('url'))
        normalized.setdefault('codigoBarras', {'linhaDigitavel': bank_slip.get('digitable')})
        normalized.setdefault('pix', {'copiaECola': pix.get('emv')})
        return normalized

    def _raise_for_status(self, response, action):
        if response.status_code >= 400:
            raise OnlineBankAPIError(
                f'Erro ao {action} boleto ({self.bank_name}): HTTP {response.status_code} - {response.text}'
            )

    def _to_cora_payload(self, payload):
        data = payload if isinstance(payload, dict) else {}
        pagador = data.get('pagador') if isinstance(data.get('pagador'), dict) else {}

        valor = data.get('valor')
        try:
            total_amount = int(round(float(valor or 0) * 100))
        except Exception:
            total_amount = 0
        if total_amount <= 0:
            total_amount = 500

        nome = str(pagador.get('nome') or '').strip()[:60] or 'Cliente'
        documento = str(pagador.get('documento') or '').strip()
        doc_digits = ''.join(ch for ch in documento if ch.isdigit())
        doc_type = 'CNPJ' if len(doc_digits) > 11 else 'CPF'

        seu_numero = str(data.get('seuNumero') or data.get('numeroDocumento') or self._uuid()).strip()
        vencimento = str(data.get('dataVencimento') or '').strip()

        return {
            'code': seu_numero,
            'customer': {
                'name': nome,
                'document': {
                    'identity': doc_digits,
                    'type': doc_type,
                },
            },
            'services': [
                {
                    'name': f'Título {seu_numero}',
                    'amount': total_amount,
                }
            ],
            'payment_terms': {
                'due_date': vencimento,
                'type': 'NET',
            },
            'payment_forms': ['BANK_SLIP'],
        }

    def registrar_boleto(self, payload):
        token = self._token()
        headers = self._headers(token)
        headers['Idempotency-Key'] = self._uuid()
        cora_payload = self._to_cora_payload(payload)
        r = requests.post(f'{self.boletos_url()}/', json=cora_payload, headers=headers, timeout=45)
        self._raise_for_status(r, 'registrar')
        return self._normalize_response(r.json() if r.text else {})

    def consultar_boleto(self, nosso_numero):
        token = self._token()
        invoice_id = str(nosso_numero or '').strip()
        r = requests.get(f"{self.boletos_url()}/{invoice_id}", headers=self._headers(token), timeout=30)
        self._raise_for_status(r, 'consultar')
        return self._normalize_response(r.json() if r.text else {})

    def alterar_boleto(self, nosso_numero, payload):
        token = self._token()
        invoice_id = str(nosso_numero or '').strip()
        data_vencimento = ''
        if isinstance(payload, dict):
            data_vencimento = str(
                payload.get('dataVencimento') or payload.get('novoVencimento') or payload.get('vencimento') or ''
            ).strip()

        candidates = [
            {'payment_terms': {'due_date': data_vencimento}},
            {'due_date': data_vencimento},
        ]
        errors = []
        for body in candidates:
            for method in ('patch', 'put'):
                req = requests.patch if method == 'patch' else requests.put
                r = req(f"{self.boletos_url()}/{invoice_id}", json=body, headers=self._headers(token), timeout=30)
                if r.status_code < 400:
                    return self._normalize_response(r.json() if r.text else {'ok': True})
                errors.append(f'{method.upper()} {r.status_code}')

        raise OnlineBankAPIError(f'Erro ao alterar boleto ({self.bank_name}): ' + ' | '.join(errors))

    def cancelar_boleto(self, nosso_numero, payload=None):
        token = self._token()
        invoice_id = str(nosso_numero or '').strip()
        r = requests.delete(f"{self.boletos_url()}/{invoice_id}", headers=self._headers(token), timeout=30)
        self._raise_for_status(r, 'cancelar')
        return r.json() if r.text else {'ok': True}

    def baixar_boleto(self, nosso_numero, payload=None):
        return self.cancelar_boleto(nosso_numero, payload=payload)

    def obter_pdf_boleto(self, nosso_numero, linha_digitavel=None):
        data = self.consultar_boleto(nosso_numero)
        bank_slip = (((data.get('payment_options') or {}).get('bank_slip') or {}) if isinstance(data, dict) else {})
        url = str(
            data.get('linkBoleto')
            or bank_slip.get('url')
            or ''
        ).strip()
        if not url:
            raise OnlineBankAPIError('Cora não retornou URL de PDF para este boleto.')

        r = requests.get(url, headers={'Accept': 'application/pdf'}, timeout=45)
        if r.status_code >= 400:
            raise OnlineBankAPIError(f'Erro ao obter PDF do boleto ({self.bank_name}): HTTP {r.status_code}')
        if not (r.content or b'').startswith(b'%PDF'):
            raise OnlineBankAPIError('Resposta de impressão da Cora não é um PDF válido.')
        return r.content
