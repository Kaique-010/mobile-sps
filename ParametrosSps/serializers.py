from rest_framework import serializers
from .models import Parametros


class ParametrosPedidosSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parametros
        fields = ['pedido_cancelamento_habilitado']
