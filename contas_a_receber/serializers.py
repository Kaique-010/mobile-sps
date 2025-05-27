from rest_framework import serializers
from .models import Titulosreceber



class TitulosreceberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Titulosreceber
        fields = [
            'titu_empr',
            'titu_titu',
            'titu_seri',
            'titu_parc',
            'titu_clie',
            'titu_valo',
            'titu_venc',
            'titu_situ',
            'titu_form_reci'
     
            
        ]