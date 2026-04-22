from .online_bank_api_base import BaseOnlineBankAPIView, BaseOnlineBankTokenAPIView


class BradescoTokenAPIView(BaseOnlineBankTokenAPIView):
    bank_code = '237'


class BradescoBoletoAPIView(BaseOnlineBankAPIView):
    bank_code = '237'
