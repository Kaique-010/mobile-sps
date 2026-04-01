from .sicredi_api_service import SicrediCobrancaService, SicrediAPIError
from .online_banks import (
    OnlineBankAPIError,
    BradescoCobrancaService,
    ItauCobrancaService,
    BancoBrasilCobrancaService,
    CoraCobrancaService,
    BTGPactualCobrancaService,
)

SUPPORTED_BANKS = {
    '748': 'Sicredi',
    '237': 'Bradesco',
    '341': 'Itaú',
    '001': 'Banco do Brasil',
    '403': 'Cora',
    '208': 'BTG Pactual',
}


SERVICE_BY_BANK = {
    '237': BradescoCobrancaService,
    '341': ItauCobrancaService,
    '001': BancoBrasilCobrancaService,
    '403': CoraCobrancaService,
    '208': BTGPactualCobrancaService,
}


def get_online_boleto_service(bank_code, carteira):
    code = str(bank_code)
    if code == '748':
        return SicrediCobrancaService(carteira), SicrediAPIError

    service_cls = SERVICE_BY_BANK.get(code)
    if not service_cls:
        raise OnlineBankAPIError(f'Banco {code} não suportado para registros online.')

    return service_cls(carteira), OnlineBankAPIError
