from rest_framework import serializers
from .models import Titulospagar

class TitulospagarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Titulospagar
        fields = [
            'titu_empr',
            'titu_titu',
            'titu_seri',
            'titu_parc',
            'titu_forn',
            'titu_valo',
            'titu_venc',
            'titu_situ',
            'titu_usua_lanc',
            'titu_form_reci'
        ]

