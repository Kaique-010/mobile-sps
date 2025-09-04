from rest_framework import serializers
from rest_framework.exceptions import ValidationError
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
            # Verificar se a data é válida antes de fazer a query
            if hasattr(obj, 'entr_data') and obj.entr_data:
                try:
                    # Tentar acessar o ano da data para verificar se é válida
                    year = obj.entr_data.year
                    if year < 1900:
                        logger.warning(f"Data inválida no registro {obj.entr_sequ}: {obj.entr_data}")
                        return "Produto com data inválida"
                except (ValueError, AttributeError) as date_error:
                    logger.warning(f"Erro na data do registro {obj.entr_sequ}: {date_error}")
                    return "Produto com data inválida"
            
            produto = Produtos.objects.using(banco).filter(
                prod_codi=obj.entr_prod,
                prod_empr=obj.entr_empr
            ).first()
            return produto.prod_nome if produto else None
        except Produtos.DoesNotExist:
            logger.warning(f"Produto com ID {obj.entr_prod} não encontrado.")
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar produto para entrada {obj.entr_sequ}: {e}")
            return None

    def get_empresa_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None
        try:
            empresa = Empresas.objects.using(banco).filter(
                empr_codi=obj.entr_empr
            ).first()
            return empresa.empr_nome if empresa else None
        except Exception as e:
            logger.error(f"Erro ao buscar empresa: {e}")
            return None

    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco não especificado no contexto")
        
        # Gerar próximo número sequencial
        max_sequ = EntradaEstoque.objects.using(banco).aggregate(
            max_sequ=Max('entr_sequ')
        )['max_sequ'] or 0
        validated_data['entr_sequ'] = max_sequ + 1
        
        return EntradaEstoque.objects.using(banco).create(**validated_data)

    def update(self, instance, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco não especificado no contexto")
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=banco)
        return instance
