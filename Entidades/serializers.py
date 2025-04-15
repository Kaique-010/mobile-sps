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

    def create(self, validated_data):
        # empresa e filial já devem estar presentes
        empresa = validated_data.get('enti_empr')
        filial = validated_data.get('enti_fili')

        # Verifica se o campo enti_clie não foi enviado, e gera automaticamente
        if not validated_data.get('enti_clie'):
            ultimo = Entidades.objects.filter(
                enti_empr=empresa,
                enti_fili=filial
            ).order_by('-enti_clie').first()
            
            
            print(f"Ultimo valor de enti_clie: {ultimo.enti_clie if ultimo else 'Nenhum registrado'}")

            validated_data['enti_clie'] = (ultimo.enti_clie + 1) if ultimo else 1

        # Agora, chama o método create do serializer que irá salvar a instância
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('enti_clie', None)
        return super().update(instance, validated_data)
