# financeiro/api/serializers/orcamento_serializer.py
from rest_framework import serializers


class OrcamentoResumoFiltroSerializer(serializers.Serializer):
    orcamento_id = serializers.IntegerField()
    ano = serializers.IntegerField()
    mes = serializers.IntegerField()


class OrcamentoItemSerializer(serializers.Serializer):
    centro_custo_id = serializers.IntegerField()
    centro_custo_nome = serializers.CharField()
    tipo = serializers.CharField()
    previsto = serializers.DecimalField(max_digits=15, decimal_places=2)
    realizado = serializers.DecimalField(max_digits=15, decimal_places=2)
    saldo = serializers.DecimalField(max_digits=15, decimal_places=2)
    percentual = serializers.DecimalField(max_digits=8, decimal_places=2)


class OrcamentoSalvarSerializer(serializers.Serializer):
    orcamento_id = serializers.IntegerField()
    centro_custo_id = serializers.IntegerField()
    ano = serializers.IntegerField()
    mes = serializers.IntegerField()
    valor = serializers.DecimalField(max_digits=15, decimal_places=2)
    observacao = serializers.CharField(max_length=255, required=False)