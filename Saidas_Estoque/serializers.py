import logging
from rest_framework import serializers
from django.db.models import Max
from .models import SaidasEstoque
from Produtos.models import Produtos
from Licencas.models  import Empresas


logger = logging.getLogger(__name__)

class SaidasEstoqueSerializer(serializers.ModelSerializer):
    empresa_nome = serializers.SerializerMethodField()
    produto_nome = serializers.SerializerMethodField()

    class Meta:
        model = SaidasEstoque
        fields = '__all__'
        extra_kwargs = {
            'said_sequ': {'read_only': True}
        }

    def get_produto_nome(self, obj):
        try:
            return Produtos.objects.get(prod_codi=obj.said_prod).prod_nome
        except Produtos.DoesNotExist:
            return None

    def get_empresa_nome(self, obj):
        try:
            return Empresas.objects.get(empr_codi=obj.said_empr).empr_nome
        except Empresas.DoesNotExist:
            return None

    def create(self, validated_data):
        logger.info(f" [CREATE] Dados recebidos: {validated_data}")
        if not validated_data.get('said_sequ'):
            max_seq = SaidasEstoque.objects.aggregate(Max('said_sequ'))['said_sequ__max'] or 0
            validated_data['said_sequ'] = max_seq + 1
            logger.info(f" Sequência gerada automaticamente: {validated_data['said_sequ']}")
        try:
            instance = super().create(validated_data)
            logger.info(f" Saída criada com sucesso: ID={instance}")
            return instance
        except Exception as e:
            logger.error(f" Erro ao criar saída: {str(e)}")
            raise

    def update(self, instance, validated_data):
        logger.info(f" [UPDATE] Atualizando ID={instance} com dados: {validated_data}")
        try:
            instance = super().update(instance, validated_data)
            logger.info(f"✅ Saída atualizada com sucesso: ID={instance.id}")
            return instance
        except Exception as e:
            logger.error(f" Erro ao atualizar saída ID={instance.id}: {str(e)}")
            raise

    def destroy(self, instance):
        logger.info(f"[DELETE] Tentando excluir Saída ID={instance}")
        try:
            instance.delete()
            logger.info(f"✅ saída excluída com sucesso: ID={instance}")
        except Exception as e:
            logger.error(f"Erro ao excluir saída ID={instance}: {str(e)}")
            raise
