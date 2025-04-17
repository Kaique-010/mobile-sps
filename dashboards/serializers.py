# dashboards/serializers.py
from rest_framework import serializers

class SaldoProdutoSerializer(serializers.Serializer):
    nome = serializers.CharField(max_length=255)
    total = serializers.DecimalField(max_digits=10, decimal_places=2)

class PedidoVendaSerializer(serializers.Serializer):
    cliente = serializers.CharField(max_length=255)
    total = serializers.DecimalField(max_digits=15, decimal_places=2)

class DashboardSerializer(serializers.Serializer):
    saldos_produto = SaldoProdutoSerializer(many=True)
    pedidos_por_cliente = PedidoVendaSerializer(many=True)
