from .base import BaseOAuthBoletoService


class BradescoCobrancaService(BaseOAuthBoletoService):
    bank_code = 'BRADESCO'
    bank_name = 'Bradesco'

    def default_token_path(self):
        return '/oauth/token'

    def default_boletos_path(self):
        return '/v1/boletos'
