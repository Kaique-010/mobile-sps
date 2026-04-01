from .base import BaseOAuthBoletoService


class ItauCobrancaService(BaseOAuthBoletoService):
    bank_code = 'ITAU'
    bank_name = 'Itaú'

    def default_token_path(self):
        return '/oauth/token'

    def default_boletos_path(self):
        return '/v1/boletos'
