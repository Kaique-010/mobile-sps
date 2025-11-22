from rest_framework import serializers
from ...models import Titulosreceber


class TituloReceberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Titulosreceber  
        fields = [
        'titu_empr', 'titu_fili', 'titu_clie',
        'titu_titu', 'titu_seri', 'titu_parc',
        'titu_emis', 'titu_venc', 'titu_valo',
        'titu_noss_nume', 'titu_noss_nume_form',
        'titu_linh_digi', 'titu_url_bole'
        ]
