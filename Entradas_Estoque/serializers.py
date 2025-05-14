from rest_framework import serializers
from django.db.models import Max
from .models import EntradaEstoque
from Produtos.models import Produtos
from Licencas.models import Empresas
from core.serializers import BancoContextMixin
import logging

logger = logging.getLogger(__name__)

class EntradasEstoqueSerializer(BancoContextMixin, serializers.ModelSerializer):
    empresa_nome = serializers.SerializerMethodField()
    produto_nome = serializers.SerializerMethodField()

    class Meta:
        model = EntradaEstoque
        fields = '__all__'
        extra_kwargs = {
            'entr_sequ': {'read_only': True}
        }

    def get_produto_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None
        try:
            return Produtos.objects.using(banco).get(prod_codi=obj.entr_prod).prod_nome
        except Produtos.DoesNotExist:
            logger.warning(f"Produto com ID {obj.entr_prod} não encontrado.")
            return None
        

    def get_empresa_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None

        try:
            return Empresas.objects.using(banco).get(empr_codi=obj.entr_empr).empr_nome
        except Empresas.DoesNotExist:
            logger.warning(f"Empresa com ID {obj.entr_empr} não encontrada.")
            return None
       


    def create(self, validated_data):
        if not validated_data.get('entr_sequ'):
            max_seq = self.using_queryset(EntradaEstoque).aggregate(Max('entr_sequ'))['entr_sequ__max'] or 0
            validated_data['entr_sequ'] = max_seq + 1
        try:
            instance = self.using_queryset(EntradaEstoque).create(**validated_data)
            return instance
        except Exception as e:
            logger.error(f"Erro ao criar entrada: {str(e)}")
            raise
        

    def update(self, instance, validated_data):
        try:
            instance = super().update(instance, validated_data)
            return instance
        except Exception as e:
            logger.error(f"Erro ao atualizar entrada ID={instance.id}: {str(e)}")
            raise
