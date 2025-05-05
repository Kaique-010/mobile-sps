# serializers.py
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.db import models

from Produtos.models import Produtos
from .utils import get_next_item_number
from Licencas.models import Empresas
from .models import ListaCasamento, ItensListaCasamento

class ItensListaCasamentoSerializer(serializers.ModelSerializer):
    produto_nome = serializers.SerializerMethodField(read_only=True)
    item_item = serializers.IntegerField(read_only=True)  # O AutoField será preenchido automaticamente
    item_prod = serializers.PrimaryKeyRelatedField(queryset=Produtos.objects.all())  # Serializa a chave primária do produto
    log_time = serializers.TimeField(read_only=True)
    log_data = serializers.DateField(read_only=True)

    class Meta:
        model = ItensListaCasamento
        fields = '__all__'

    def get_queryset(self):
        queryset = super().get_queryset()
        item_list = self.request.query_params.get('item_list', None)
        if item_list is not None:
            queryset = queryset.filter(item_list=item_list)
        return queryset
    
    def get_produto_nome(self, obj):
        try:
            return Produtos.objects.get(prod_codi=obj.item_prod).prod_nome
        except Produtos.DoesNotExist:
            return None

    def create(self, validated_data):
        item_empr = validated_data['item_empr']
        item_fili = validated_data['item_fili']
        item_list = validated_data['item_list']

        validated_data['item_item'] = get_next_item_number(item_empr, item_fili, item_list)
        return ItensListaCasamento.objects.create(**validated_data)




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
