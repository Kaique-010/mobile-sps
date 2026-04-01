from types import SimpleNamespace

from django.test import SimpleTestCase

from boletos.services.boleto_online_factory import SUPPORTED_BANKS, get_online_boleto_service
from boletos.services.online_banks import BradescoCobrancaService
from boletos.services.sicredi_api_service import SicrediCobrancaService


class BoletoOnlineFactoryTests(SimpleTestCase):
    def test_supported_banks_contem_bancos_solicitados(self):
        for code in ['748', '237', '341', '001', '403', '208']:
            self.assertIn(code, SUPPORTED_BANKS)

    def test_factory_retorna_servico_sicredi_para_748(self):
        carteira = SimpleNamespace()
        service, _ = get_online_boleto_service('748', carteira)
        self.assertIsInstance(service, SicrediCobrancaService)

    def test_factory_retorna_servico_dedicado_para_bradesco(self):
        carteira = SimpleNamespace()
        service, _ = get_online_boleto_service('237', carteira)
        self.assertIsInstance(service, BradescoCobrancaService)
