from rest_framework import serializers
from transportes.models import Cte

class CteCargaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cte
        fields = [
            'id', 'total_mercadoria', 'produto_predominante', 'unidade_medida',
            'tipo_medida', 'numero_contrato', 'numero_lacre',
            'data_previsao_entrega', 'ncm', 'total_peso'
        ]
