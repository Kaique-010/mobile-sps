from rest_framework import serializers

from .models import Obra, ObraEtapa, ObraLancamentoFinanceiro, ObraMaterialMovimento, ObraProcesso


class ObraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Obra
        fields = "__all__"


class ObraEtapaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObraEtapa
        fields = "__all__"


class ObraMaterialMovimentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObraMaterialMovimento
        fields = "__all__"


class ObraLancamentoFinanceiroSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObraLancamentoFinanceiro
        fields = "__all__"


class ObraProcessoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObraProcesso
        fields = "__all__"
