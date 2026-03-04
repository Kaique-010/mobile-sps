from rest_framework import serializers
from transportes.models import Cte

class CteTipoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cte
        fields = [
            'id', 'tomador_servico', 'tipo_servico', 'tipo_cte', 'forma_emissao',
            'tipo_frete', 'redespacho', 'subcontratado', 'outro_tomador', 'transportadora'
        ]
