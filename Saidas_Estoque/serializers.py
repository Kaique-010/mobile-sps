import logging
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.db.models import Max
from .models import SaidasEstoque
from Produtos.models import Produtos
from Licencas.models import Empresas
from core.serializers import BancoContextMixin  # nosso mixin
from datetime import datetime

logger = logging.getLogger(__name__)

class SaidasEstoqueSerializer(BancoContextMixin, serializers.ModelSerializer):
    empresa_nome = serializers.SerializerMethodField()
    produto_nome = serializers.SerializerMethodField()

    class Meta:
        model = SaidasEstoque
        fields = '__all__'
        extra_kwargs = {
            'said_sequ': {'read_only': True}
        }

    def get_produto_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None
        
        try:
            # Validar se obj tem data válida antes de fazer a query
            if hasattr(obj, 'said_data') and obj.said_data:
                try:
                    # Tentar converter a data para verificar se é válida
                    if isinstance(obj.said_data, str):
                        datetime.strptime(obj.said_data, '%Y-%m-%d')
                    elif hasattr(obj.said_data, 'year') and obj.said_data.year < 1:
                        logger.warning(f"Data inválida encontrada para saída {obj.said_sequ}: {obj.said_data}")
                        return "Produto com data inválida"
                except (ValueError, TypeError) as date_error:
                    logger.warning(f"Erro de data na saída {obj.said_sequ}: {date_error}")
                    return "Produto com data inválida"
            
            produto = Produtos.objects.using(banco).filter(
                prod_codi=obj.said_prod,
                prod_empr=obj.said_empr, 
              
            ).first()
            return produto.prod_nome if produto else None
            
        except ValueError as ve:
            if "year" in str(ve) and "out of range" in str(ve):
                logger.error(f"Erro de data inválida na saída {obj.said_sequ}: {ve}")
                return "Produto com data inválida"
            logger.error(f"Erro de valor na saída {obj.said_sequ}: {ve}")
            return None
        except Produtos.DoesNotExist:
            logger.warning(f"Produto com ID {obj.said_prod} não encontrado.")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar produto para saída {obj.said_sequ}: {e}")
            return None
        

    def get_empresa_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None

        try:
            return Empresas.objects.using(banco).get(empr_codi=obj.said_empr).empr_nome
        except Empresas.DoesNotExist:
            logger.warning(f"Empresa com ID {obj.said_empr} não encontrada.")
            return None

    def create(self, validated_data):
        banco = self.context.get('banco')
        
        if not banco:
            raise ValidationError("Banco de dados não informado no contexto.")

        if not validated_data.get('said_sequ'):
            max_seq = SaidasEstoque.objects.using(banco).aggregate(Max('said_sequ'))['said_sequ__max'] or 0
            validated_data['said_sequ'] = max_seq + 1
        try:
            instance = SaidasEstoque.objects.using(banco).create(**validated_data)
            return instance
        except Exception as e:
            logger.error(f"Erro ao criar saída: {str(e)}")
            raise
    
    


    def update(self, instance, validated_data):
        logger.info(f"[UPDATE] Atualizando ID={instance.pk} com dados: {validated_data}")
        try:
            # Assumindo que a view buscou a instância via using_queryset,
            # super().update() já salva no banco correto.
            instance = super().update(instance, validated_data)
            logger.info(f"✅ Saída atualizada com sucesso: ID={instance.pk}")
            return instance
        except Exception as e:
            logger.error(f"Erro ao atualizar saída ID={instance.pk}: {e}")
            raise
