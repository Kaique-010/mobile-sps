from rest_framework import serializers
from .models import Entidades

class EntidadesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Entidades
        fields = '__all__'

    def validate(self, data):
        erros = {}

        # Lista de campos obrigatórios personalizados
        obrigatorios = ['enti_nome', 'enti_cep', 'enti_ende', 'enti_nume', 'enti_cida', 'enti_esta'] 
        
        for campo in obrigatorios:
            if not data.get(campo):
                erros[campo] = ['Este Campo é Obrigatório.']
        
        if erros:
            raise serializers.ValidationError(erros)
        
        return data
