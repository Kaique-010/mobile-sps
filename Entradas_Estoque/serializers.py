import logging
from rest_framework import serializers
from django.db.models import Max
from .models import EntradaEstoque
from Produtos.models import Produtos
from Licencas.models import Empresas

logger = logging.getLogger(__name__)

class EntradasEstoqueSerializer(serializers.ModelSerializer):
    empresa_nome = serializers.SerializerMethodField()
    produto_nome = serializers.SerializerMethodField()

    class Meta:
        model = EntradaEstoque
        fields = '__all__'
        extra_kwargs = {
            'entr_sequ': {'read_only': True}
        }

    def get_produto_nome(self, obj):
        try:
            return Produtos.objects.get(prod_codi=obj.entr_prod).prod_nome
        except Produtos.DoesNotExist:
            logger.warning(f" Produto com ID {obj.entr_prod} não encontrado.")
            return None

    def get_empresa_nome(self, obj):
        try:
            return Empresas.objects.get(empr_codi=obj.entr_empr).empr_nome
        except Empresas.DoesNotExist:
            logger.warning(f" Empresa com ID {obj.entr_empr} não encontrada.")
            return None

    def create(self, validated_data):
        logger.info(f" [CREATE] Dados recebidos: {validated_data}")
        if not validated_data.get('entr_sequ'):
            max_seq = EntradaEstoque.objects.aggregate(Max('entr_sequ'))['entr_sequ__max'] or 0
            validated_data['entr_sequ'] = max_seq + 1
            logger.info(f" Sequência gerada automaticamente: {validated_data['entr_sequ']}")
        try:
            instance = super().create(validated_data)
            logger.info(f" Entrada criada com sucesso: ID={instance}")
            return instance
        except Exception as e:
            logger.error(f" Erro ao criar entrada: {str(e)}")
            raise

    def update(self, instance, validated_data):
        logger.info(f" [UPDATE] Atualizando ID={instance} com dados: {validated_data}")
        try:
            instance = super().update(instance, validated_data)
            logger.info(f"✅ Entrada atualizada com sucesso: ID={instance.id}")
            return instance
        except Exception as e:
            logger.error(f" Erro ao atualizar entrada ID={instance.id}: {str(e)}")
            raise

    def destroy(self, instance):
        logger.info(f"[DELETE] Tentando excluir entrada ID={instance}")
        try:
            instance.delete()
            logger.info(f"✅ Entrada excluída com sucesso: ID={instance}")
        except Exception as e:
            logger.error(f"Erro ao excluir entrada ID={instance}: {str(e)}")
            raise
