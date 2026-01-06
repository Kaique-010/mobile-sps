# serializers.py
from rest_framework import serializers

class RegistroPontoInputSerializer(serializers.Serializer):
    colaborador_id = serializers.IntegerField()
    tipo = serializers.CharField()

class RegistroPontoOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    colaborador_id = serializers.IntegerField()
    tipo = serializers.CharField()
    data_hora = serializers.DateTimeField()
    documento = serializers.CharField(required=False, allow_null=True)

    