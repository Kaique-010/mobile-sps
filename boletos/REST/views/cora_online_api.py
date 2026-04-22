from .online_bank_api_base import BaseOnlineBankAPIView, BaseOnlineBankTokenAPIView


class CoraTokenAPIView(BaseOnlineBankTokenAPIView):
    bank_code = '403'


class CoraBoletoAPIView(BaseOnlineBankAPIView):
    bank_code = '403'
