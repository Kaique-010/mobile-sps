# serializers.py
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from Licencas.models import Empresas
from .models import ListaCasamento, ItensListaCasamento

class ItensListaCasamentoSerializer(serializers.ModelSerializer):
    produto_nome = serializers.CharField(source='item_prod.nome', read_only=True)
    class Meta:
        model = ItensListaCasamento
        fields = '__all__'

class ListaCasamentoSerializer(serializers.ModelSerializer):
    itens = ItensListaCasamentoSerializer(many=True, required=False)
    cliente_nome = serializers.CharField(source='list_noiv.enti_nome', read_only=True)
    empresa_nome = serializers.SerializerMethodField()

    class Meta:
        model = ListaCasamento
        fields = '__all__'

    def validate(self, data):
        obrigatorios = ['list_noiv', 'list_data']
        erros = {
            campo: ['Este campo é obrigatório.']
            for campo in obrigatorios
            if not data.get(campo)
        }
        if erros:
            raise ValidationError(erros)
        return data

    def get_empresa_nome(self, obj):
        try:
            return Empresas.objects.get(empr_codi=obj.list_empr).empr_nome
        except Empresas.DoesNotExist:
            return None
    
    '''def create(self, validated_data):
        itens_data = validated_data.pop('itens', [])
        lista = ListaCasamento.objects.create(**validated_data)

        for item in itens_data:
            ItensListaCasamento.objects.create(

                item_list=lista.list_codi,
                **item
            )

        return lista

    def update(self, instance, validated_data):
        itens_data = validated_data.pop('itens', [])
        instance = super().update(instance, validated_data)

        existentes_ids = [item.id for item in instance.itens.all()]
        novos_ids = [item.get('id') for item in itens_data if 'id' in item]

        # Remove os que sumiram
        for item_id in set(existentes_ids) - set(novos_ids):
            ItensListaCasamento.objects.filter(id=item_id).delete()

        # Atualiza ou cria novos
        for item in itens_data:
            if 'id' in item:
                item_obj = ItensListaCasamento.objects.get(id=item['id'])
                for field, value in item.items():
                    setattr(item_obj, field, value)
                item_obj.save()
            else:
                ItensListaCasamento.objects.create(
                    item_list=instance.list_codi,
                    **item
                )

        return instance'''
