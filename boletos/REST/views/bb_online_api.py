from .online_bank_api_base import BaseOnlineBankAPIView, BaseOnlineBankTokenAPIView


class BancoBrasilTokenAPIView(BaseOnlineBankTokenAPIView):
    bank_code = '001'


class BancoBrasilBoletoAPIView(BaseOnlineBankAPIView):
    bank_code = '001'
