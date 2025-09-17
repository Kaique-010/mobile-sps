from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.db import models
from django.db.models import Max
from Produtos.models import Produtos, Tabelaprecos
from .utils import get_next_item_number
from Licencas.models import Empresas
from .models import ListaCasamento, ItensListaCasamento
from core.serializers import BancoContextMixin

import logging

logger = logging.getLogger(__name__)


class ItensListaCasamentoSerializer(BancoContextMixin, serializers.ModelSerializer):
    produto_nome = serializers.SerializerMethodField(read_only=True)
    prod_preco_vista = serializers.SerializerMethodField(read_only=True)
    item_prec = serializers.SerializerMethodField(read_only=True)
    item_item = serializers.IntegerField(read_only=True)
    item_prod = serializers.CharField(max_length=60)  # Mudança para CharField
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
            produto = Produtos.objects.using(banco).filter(
                prod_codi=obj.item_prod,
                prod_empr=obj.item_empr
            ).first()
            return produto.prod_nome if produto else None
        except Exception as e:
            logger.warning(f"Erro ao buscar produto {obj.item_prod} empresa {obj.item_empr}: {e}")
            return None
    
    def get_prod_preco_vista(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return 0.00
        try:
            # Busca o produto filtrando por código e empresa do item
            produto = Produtos.objects.using(banco).filter(
                prod_codi=obj.item_prod,
                prod_empr=obj.item_empr
            ).first()
            
            if not produto:
                logger.warning(f"Produto {obj.item_prod} empresa {obj.item_empr} não encontrado.")
                return 0.00
            
            preco = Tabelaprecos.objects.using(banco).filter(
                tabe_prod=produto.prod_codi,
                tabe_empr=obj.item_empr  # Usa a empresa do item
            ).values('tabe_avis', 'tabe_prco').first()
            
            if preco:
                # Retorna preço à vista se disponível, senão preço normal
                return float(preco['tabe_avis'] or preco['tabe_prco'] or 0.00)
            
            return 0.00
        except Exception as e:
            logger.warning(f"Erro ao buscar preço produto {obj.item_prod} empresa {obj.item_empr}: {e}")
            return 0.00
    
    def get_item_prec(self, obj):
        """Retorna o preço unitário do item (mesmo que prod_preco_vista)"""
        return self.get_prod_preco_vista(obj)

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
            empresa = Empresas.objects.using(banco).filter(empr_codi=obj.list_empr).first()
            return empresa.empr_nome if empresa else None
        except Exception as e:
            logger.warning(f"Erro ao buscar empresa {obj.list_empr}: {e}")
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