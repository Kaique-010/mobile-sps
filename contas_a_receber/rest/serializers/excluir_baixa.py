from rest_framework import serializers


class ExcluirBaixaSerializer(serializers.Serializer):
    motivo_exclusao = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    def validate_confirmar_exclusao(self, value):
        if not value:
            raise serializers.ValidationError("É necessário confirmar a exclusão da baixa")
        return value