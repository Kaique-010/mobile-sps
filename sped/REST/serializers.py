from rest_framework import serializers


class GerarSpedSerializer(serializers.Serializer):
    empresa_id = serializers.IntegerField(required=False)
    filial_id = serializers.IntegerField(required=False)
    data_inicio = serializers.DateField(input_formats=["%Y-%m-%d", "%d/%m/%Y"])
    data_fim = serializers.DateField(input_formats=["%Y-%m-%d", "%d/%m/%Y"])
    cod_receita = serializers.CharField(required=False, allow_blank=True)
    data_vencimento = serializers.DateField(required=False, input_formats=["%Y-%m-%d", "%d/%m/%Y"])
