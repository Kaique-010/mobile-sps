from rest_framework import serializers
from transportes.models import Cte

class CteSeguroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cte
        fields = [
            'id', 'seguro_por_conta', 'seguradora', 'valor_base_seguro',
            'numero_apolice', 'numero_averbado', 'percentual_seguro', 'cte_valor_seguro'
        ]
