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


class BaixaEmMassaTitulosFiltroSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=[("pagar", "pagar"), ("receber", "receber")])
    data_ini = serializers.DateField(required=False)
    data_fim = serializers.DateField(required=False)
    q = serializers.CharField(required=False, allow_blank=True)


class BaixaEmMassaExecutarSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=[("pagar", "pagar"), ("receber", "receber")])
    ids = serializers.ListField(child=serializers.CharField(), allow_empty=False)
    data_baixa = serializers.DateField()
    banco_id = serializers.IntegerField()
    centro_custo = serializers.IntegerField(required=False, allow_null=True)
    forma_pagamento = serializers.CharField(required=False, allow_blank=True, default="B")
    usuario_id = serializers.IntegerField(required=False, allow_null=True)
    valor_juros = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, default="0.00")
    valor_multa = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, default="0.00")
    valor_desconto = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, default="0.00")
    historico = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    cheque = serializers.IntegerField(required=False, allow_null=True)
