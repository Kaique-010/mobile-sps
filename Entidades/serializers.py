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

        # Garantir que o campo `enti_clie` seja preenchido com o valor sequencial correto
        if not data.get('enti_clie'):
            # Buscar o último valor de `enti_clie` da empresa e filial atual (ou qualquer critério que você utilize para isso)
            ultimo_enti_clie = Entidades.objects.filter(
                empresa=data.get('empresa'), filial=data.get('filial')
            ).order_by('-enti_clie').first()

            # Gerar o próximo valor sequencial
            if ultimo_enti_clie:
                data['enti_clie'] = ultimo_enti_clie.enti_clie + 1
            else:
                data['enti_clie'] = 1  # Caso não haja registros, iniciar com 1

        return data
