from rest_framework import serializers
from ...models import Boleto


class BoletoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Boleto
        fields = [
        'bole_empr', 'bole_fili', 'bole_soci',
        'bole_titu', 'bole_seri', 'bole_parc',
        'bole_emis', 'bole_venc', 'bole_valo',
        'bole_noss', 'bole_linh_digi', 'bole_nome_arqu'
        ]