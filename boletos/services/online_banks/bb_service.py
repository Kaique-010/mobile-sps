from .base import BaseOAuthBoletoService


class BancoBrasilCobrancaService(BaseOAuthBoletoService):
    bank_code = 'BB'
    bank_name = 'Banco do Brasil'

    def default_token_path(self):
        return '/oauth/token'

    def default_boletos_path(self):
        return '/v1/boletos'
