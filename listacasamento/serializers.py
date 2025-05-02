# serializers.py
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.db import models
from .utils import get_next_item_number
from Licencas.models import Empresas
from .models import ListaCasamento, ItensListaCasamento

class ItensListaCasamentoSerializer(serializers.ModelSerializer):
    produto_nome = serializers.SerializerMethodField(read_only=True)
    item_item = serializers.IntegerField(read_only=True)
    item_prod = serializers.IntegerField()
    class Meta:
        model = ItensListaCasamento
        fields = '__all__'
      
    
    def get_produto_nome(self, obj):
     return getattr(obj.item_prod, 'prod_nome', None)

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
    
    def perform_bulk_create(self, serializer):
        try:
            serializer.save()
        except Exception as e:
            print('[ERRO] Falha ao salvar itens em massa:', e)
            raise
