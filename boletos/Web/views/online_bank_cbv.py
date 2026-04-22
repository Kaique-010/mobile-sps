from .online_cbv import BoletoOnlineView


class SicrediBoletoOnlineView(BoletoOnlineView):
    template_name = 'Boletos/online_registros_sicredi.html'
    forced_bank_code = '748'


class BradescoBoletoOnlineView(BoletoOnlineView):
    template_name = 'Boletos/online_registros_bradesco.html'
    forced_bank_code = '237'


class ItauBoletoOnlineView(BoletoOnlineView):
    template_name = 'Boletos/online_registros_itau.html'
    forced_bank_code = '341'


class BancoBrasilBoletoOnlineView(BoletoOnlineView):
    template_name = 'Boletos/online_registros_bb.html'
    forced_bank_code = '001'


class CoraBoletoOnlineView(BoletoOnlineView):
    template_name = 'Boletos/online_registros_cora.html'
    forced_bank_code = '403'
