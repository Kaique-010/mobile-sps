from .online_bank_api_base import BaseOnlineBankAPIView, BaseOnlineBankTokenAPIView


class SicrediTokenAPIView(BaseOnlineBankTokenAPIView):
    bank_code = '748'


class SicrediBoletoAPIView(BaseOnlineBankAPIView):
    bank_code = '748'
