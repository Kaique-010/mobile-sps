from rest_framework import serializers
from ..models import UnidadeMedida

class UnidadeMedidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadeMedida
        fields = '__all__'
