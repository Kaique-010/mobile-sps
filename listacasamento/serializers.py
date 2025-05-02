# serializers.py
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.db import models
from .utils import get_next_item_number
from Licencas.models import Empresas
from .models import ListaCasamento, ItensListaCasamento

class ItensListaCasamentoSerializer(serializers.ModelSerializer):
    produto_nome = serializers.CharField(source='item_prod.nome', read_only=True)
    class Meta:
        model = ItensListaCasamento
        fields = '__all__'
        read_only_fields = ['item_item']  

    def create(self, validated_data):
        validated_data['item_item'] = get_next_item_number(
            item_list=validated_data['item_list'],
            item_empr=validated_data['item_empr'],
            item_fili=validated_data['item_fili'],
        )
        return super().create(validated_data)


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
    
    def perform_create(self, serializer):
        db_alias = getattr(self.request, 'db_alias', 'default')
        max_id = ListaCasamento.objects.using(db_alias).aggregate(models.Max('list_codi'))['list_codi__max']or 0
        serializer.save(list_codi=max_id+1)