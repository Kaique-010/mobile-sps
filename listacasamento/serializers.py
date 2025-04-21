# serializers.py
from rest_framework import serializers
from .models import ListaCasamento, ItensListaCasamento
from rest_framework.permissions import IsAuthenticated

class ItensListaCasamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItensListaCasamento
        fields = '__all__'

class ListaCasamentoSerializer(serializers.ModelSerializer):
    permission_classes = [IsAuthenticated]
    itens = ItensListaCasamentoSerializer(many=True, required=False)

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
            raise serializers.ValidationError(erros)

        return data
    
    
    def create(self, validated_data):
        itens_data = validated_data.pop('itens', [])
        lista = ListaCasamento.objects.create(**validated_data)
        for item in itens_data:
            ItensListaCasamento.objects.create(item_list=lista, **item)
        return lista

    def update(self, instance, validated_data):
        itens_data = validated_data.pop('itens', [])
        instance = super().update(instance, validated_data)

        instance.itens.all().delete()
        for item in itens_data:
            ItensListaCasamento.objects.create(item_list=instance, **item)

        return instance