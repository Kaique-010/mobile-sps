from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.db import models
from django.db.models import Max
from Produtos.models import Produtos
from .utils import get_next_item_number
from Licencas.models import Empresas
from .models import ListaCasamento, ItensListaCasamento
from core.serializers import BancoContextMixin

import logging

logger = logging.getLogger(__name__)


class ItensListaCasamentoSerializer(BancoContextMixin, serializers.ModelSerializer):
    produto_nome = serializers.SerializerMethodField(read_only=True)
    item_item = serializers.IntegerField(read_only=True)
    item_prod = serializers.PrimaryKeyRelatedField(queryset=Produtos.objects.all())
    log_time = serializers.TimeField(read_only=True)
    log_data = serializers.DateField(read_only=True)

    class Meta:
        model = ItensListaCasamento
        fields = '__all__'

    def validate(self, attrs):
      
        item_pedi = attrs.get('item_pedi', 0)
        if item_pedi != 0:
            raise serializers.ValidationError({"item_pedi": "item_pedi deve ser igual a 0."})
        attrs['item_pedi'] = 0
        
        item_quan = attrs.get('item_quan', 0)
        if item_quan <= 0:
            raise serializers.ValidationError({"item_quan": "item_quan deve ser maior que 0."})
        attrs['item_quan'] = item_quan
        
        return attrs
    
    def get_produto_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None
        try:
            return Produtos.objects.using(banco).get(prod_codi=obj.item_prod).prod_nome
        except Produtos.DoesNotExist:
            logger.warning(f"Produto com ID {obj.item_prod} não encontrado.")
            return None

    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            return None
        
        item_empr = validated_data['item_empr']
        item_fili = validated_data['item_fili']
        item_list = validated_data['item_list']

        validated_data['item_item'] = get_next_item_number(item_empr, item_fili, item_list, banco)
        return ItensListaCasamento.objects.using(banco).create(**validated_data)


class ListaCasamentoSerializer(BancoContextMixin, serializers.ModelSerializer):
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
        banco = self.context.get('banco')
        if not banco:
            return None

        try:
            return Empresas.objects.using(banco).get(empr_codi=obj.list_empr).empr_nome
        except Empresas.DoesNotExist:
            logger.warning(f"Empresa com ID {obj.list_empr} não encontrada.")
            return None

    def perform_bulk_create(self, serializer):
        try:
            serializer.save()
        except Exception as e:
            print('[ERRO] Falha ao salvar itens em massa:', e)
            raise
    
    def create(self, validated_data):
        banco = self.context.get('banco')
        
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")
        
        
        if not validated_data.get('list_codi'):
            list_codi = ListaCasamento.objects.using(banco).aggregate(Max('list_codi'))['list_codi__max'] or 0
            validated_data['list_codi'] = list_codi + 1
        return ListaCasamento.objects.using(banco).create(**validated_data)