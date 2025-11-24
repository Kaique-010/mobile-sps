from rest_framework import serializers


class ExcluirBaixaSerializer(serializers.Serializer):
    confirmar_exclusao = serializers.BooleanField(required=True)
    motivo_exclusao = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    def validate(self, data):
        if not data.get('confirmar_exclusao'):
            raise serializers.ValidationError("É necessário confirmar a exclusão da baixa")
        return data