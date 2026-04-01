from .base import BaseOAuthBoletoService


class CoraCobrancaService(BaseOAuthBoletoService):
    bank_code = 'CORA'
    bank_name = 'Cora'

    def default_token_path(self):
        return '/oauth/token'

    def default_boletos_path(self):
        return '/v1/boletos'
