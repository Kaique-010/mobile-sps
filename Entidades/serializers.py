from rest_framework import serializers
from .models import Entidades

class EntidadesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Entidades
        fields = '__all__'

    def validate(self, data):
        erros = {}
        obrigatorios = ['enti_nome', 'enti_cep', 'enti_ende', 'enti_nume', 'enti_cida', 'enti_esta']

        for campo in obrigatorios:
            if not data.get(campo):
                erros[campo] = ['Este Campo é Obrigatório.']

        if erros:
            raise serializers.ValidationError(erros)

        return data

    def update(self, instance, validated_data):
        # Garante que o campo sequencial não seja modificado no update
        validated_data.pop('enti_clie', None)
        return super().update(instance, validated_data)
