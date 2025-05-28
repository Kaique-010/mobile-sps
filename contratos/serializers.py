from rest_framework import serializers
from .models import Contratosvendas


class ContratosvendasSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Contratosvendas
        fields = [
                    'cont_cont',
                    'cont_clie',
                    'cont_data',
                    'cont_prod',
                
                ]
