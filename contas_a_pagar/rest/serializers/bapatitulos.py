from rest_framework import serializers
from ...models import Bapatitulos


class BapatitulosSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bapatitulos
        fields = [
            'bapa_sequ', 'bapa_ctrl', 'bapa_empr', 'bapa_fili', 'bapa_forn',
            'bapa_titu', 'bapa_seri', 'bapa_parc', 'bapa_dpag', 'bapa_apag',
            'bapa_vmul', 'bapa_vjur', 'bapa_vdes', 'bapa_pago', 'bapa_valo_pago',
            'bapa_sub_tota', 'bapa_topa', 'bapa_form', 'bapa_banc', 'bapa_cheq', 
            'bapa_hist', 'bapa_emis', 'bapa_venc'
        ]