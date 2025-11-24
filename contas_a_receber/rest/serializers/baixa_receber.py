from rest_framework import serializers


class BaixaTitulosReceberSerializer(serializers.Serializer):
    data_recebimento = serializers.DateField()
    valor_recebido = serializers.DecimalField(max_digits=15, decimal_places=2)
    valor_juros = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    valor_multa = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    valor_desconto = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    historico = serializers.CharField(max_length=500, required=False, allow_blank=True)
    banco = serializers.IntegerField(required=False, allow_null=True)
    cheque = serializers.IntegerField(required=False, allow_null=True)
    tipo_baixa = serializers.CharField(max_length=1, default='T')
    forma_pagamento = serializers.CharField(max_length=1, default='D', required=False)
    
    def validate(self, data):
        valor_recebido = data.get('valor_recebido', 0)
        if valor_recebido <= 0:
            raise serializers.ValidationError("Valor recebido deve ser maior que zero")
        return data