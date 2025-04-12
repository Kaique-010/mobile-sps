from rest_framework import serializers
from .models import PedidoVenda, Itenspedidovenda

class PedidoVendaSerializer(serializers.ModelSerializer):
    valor_total = serializers.FloatField(source='pedi_tota',  read_only=True)
    cliente_nome = serializers.CharField(source='pedi_forn.enti_nome', read_only=True)

    class Meta:
        model = PedidoVenda
        fields = '__all__'