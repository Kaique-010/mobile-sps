from .base import BaseOAuthBoletoService


class BTGPactualCobrancaService(BaseOAuthBoletoService):
    bank_code = 'BTG'
    bank_name = 'BTG Pactual'

    def default_token_path(self):
        return '/oauth/token'

    def default_boletos_path(self):
        return '/v1/boletos'
