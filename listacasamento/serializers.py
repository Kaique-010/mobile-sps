# serializers.py
from rest_framework import serializers
from .models import ListaCasamento, ItensListaCasamento
from rest_framework.exceptions import ValidationError

class ItensListaCasamentoSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ItensListaCasamento
        fields = '__all__'

class ListaCasamentoSerializer(serializers.ModelSerializer):
    itens = ItensListaCasamentoSerializer(many=True, required=False)
    cliente_nome = serializers.CharField(source='list_clie.enti_nome', read_only=True)

    class Meta:
        model = ListaCasamento
        fields = '__all__'

    def validate(self, data):
        erros = {}
        obrigatorios = ['list_clie', 'list_data']
        for campo in obrigatorios:
            if not data.get(campo):
                erros[campo] = ['Este campo é obrigatório.']

        if erros:
            raise ValidationError(erros)

        return data
    
    def create(self, validated_data):
        itens_data = validated_data.pop('itens', [])
        lista = ListaCasamento.objects.create(**validated_data)
        
        # Criação dos itens
        for item in itens_data:
            ItensListaCasamento.objects.create(item_list=lista, **item)
        
        return lista

    def update(self, instance, validated_data):
        itens_data = validated_data.pop('itens', [])
        instance = super().update(instance, validated_data)

        # Atualiza ou adiciona itens sem excluir os existentes
        existing_item_ids = [item.id for item in instance.itens.all()]
        new_item_ids = [item.get('id') for item in itens_data if 'id' in item]

        # Deleta itens que não foram mais enviados
        for item_id in set(existing_item_ids) - set(new_item_ids):
            ItensListaCasamento.objects.get(id=item_id).delete()

        # Atualiza itens existentes ou cria novos
        for item in itens_data:
            if 'id' in item:  # Atualiza os itens existentes
                item_instance = ItensListaCasamento.objects.get(id=item['id'])
                for field, value in item.items():
                    setattr(item_instance, field, value)
                item_instance.save()
            else:  # Cria novos itens
                ItensListaCasamento.objects.create(item_list=instance, **item)

        return instance
