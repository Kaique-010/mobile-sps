from .online_bank_api_base import BaseOnlineBankAPIView, BaseOnlineBankTokenAPIView


class ItauTokenAPIView(BaseOnlineBankTokenAPIView):
    bank_code = '341'


class ItauBoletoAPIView(BaseOnlineBankAPIView):
    bank_code = '341'
