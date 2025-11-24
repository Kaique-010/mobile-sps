from rest_framework import serializers
from ...models import Baretitulos


class BaretitulosSerializer(serializers.ModelSerializer):
    class Meta:
        model = Baretitulos
        fields = [
            'bare_sequ', 'bare_ctrl', 'bare_empr', 'bare_fili', 'bare_clie',
            'bare_titu', 'bare_seri', 'bare_parc', 'bare_dpag', 'bare_apag',
            'bare_vmul', 'bare_vjur', 'bare_vdes', 'bare_pago', 'bare_valo_pago',
            'bare_sub_tota', 'bare_topa', 'bare_form', 'bare_banc', 'bare_cheq', 
            'bare_hist', 'bare_emis', 'bare_venc', 'bare_usua_baix', 'bare_data_baix'
        ]