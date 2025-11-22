from rest_framework import serializers
from ...models import Remessaretorno


class RemessaRetornoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Remessaretorno
        fields = [
            'bole_banc', 'bole_cart', 'bole_noss', 'bole_linh_digi',
            'bole_nome_arqu', 'bole_data_rece', 'bole_valo_rece'
        ]
