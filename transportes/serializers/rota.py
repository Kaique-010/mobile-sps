from rest_framework import serializers
from transportes.models import Cte

class CteRotaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cte
        fields = [
            'id', 'cidade_coleta', 'cidade_entrega', 'pedagio', 'peso_total',
            'tarifa', 'frete_peso', 'frete_valor', 'outras_observacoes'
        ]
