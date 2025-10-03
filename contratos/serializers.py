from rest_framework import serializers
from rest_framework import status
from django.db.models import Max
from Entidades.models import Entidades
from Licencas.models import Empresas
from Produtos.models import Produtos
from .models import Contratosvendas
import logging

logger = logging.getLogger(__name__)


class ContratosvendasSerializer(serializers.ModelSerializer):
    produto_nome = serializers.SerializerMethodField()
    cliente_nome =  serializers.SerializerMethodField()
    empresa_nome = serializers.SerializerMethodField()
    
    class Meta:
        model = Contratosvendas
        fields = [
                    'cont_cont', 
                    'cont_empr',
                    'cont_fili',
                    'cont_clie',
                    'cont_data',
                    'cont_prod',
                    'cont_unit',
                    'cont_quan',
                    'cont_tota',
                    'produto_nome', 
                    'cliente_nome', 
                    'empresa_nome'
                ]
        read_only_fields = ['cont_cont', 'cont_empr', 'cont_fili']

    def validate(self, data):
        banco  = self.context.get ('banco')
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")
        
        erros = {}
        obrigatorios = [
                        'cont_clie',
                        'cont_data',
                        'cont_prod',
                        'cont_unit',
                        'cont_quan',
                        'cont_tota',
        ]

        for campo in obrigatorios:
            if not data.get(campo):
                erros[campo] = ['Este Campo é Obrigatório.']

        if erros:
            raise serializers.ValidationError(erros)

        return data

    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")
        
        # Define empresa/filial a partir do contexto (headers)
        empresa_id = self.context.get('empresa_id')
        filial_id = self.context.get('filial_id')
        if not empresa_id or not filial_id:
            raise serializers.ValidationError("Empresa/Filial não informadas nos headers")
        validated_data['cont_empr'] = empresa_id
        validated_data['cont_fili'] = filial_id
        
        if not validated_data.get('cont_cont'):
            max_cont = Contratosvendas.objects.using(banco).aggregate(Max('cont_cont'))['cont_cont__max'] or 0
            validated_data['cont_cont'] = max_cont + 1
        return Contratosvendas.objects.using(banco).create(**validated_data)

    def update(self, instance, validated_data):
        banco = self.context.get('banco')
        empresa_id = self.context.get('empresa_id')
        filial_id = self.context.get('filial_id')
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")
        if not empresa_id or not filial_id:
            raise serializers.ValidationError("Empresa/Filial não informadas nos headers")

        # Nunca permitir alteração de chave composta
        validated_data.pop('cont_cont', None)
        validated_data.pop('cont_empr', None)
        validated_data.pop('cont_fili', None)

        # Atualização direta via QuerySet no banco correto e com chave composta
        Contratosvendas.objects.using(banco).filter(
            cont_empr=empresa_id,
            cont_fili=filial_id,
            cont_cont=instance.cont_cont
        ).update(**validated_data)

        # Retorna instância atualizada do banco correto
        instance = Contratosvendas.objects.using(banco).get(
            cont_empr=empresa_id,
            cont_fili=filial_id,
            cont_cont=instance.cont_cont
        )
        return instance
        
    def get_cliente_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None

        try:
            entidades = Entidades.objects.using(banco).filter(
                enti_clie=obj.cont_clie,
                enti_empr=obj.cont_empr,
            ).first()

            return entidades.enti_nome if entidades else None

        except Exception as e:
            logger.warning(f"Erro ao buscar cliente: {e}")
            return None

    def get_empresa_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None

        try:
            return Empresas.objects.using(banco).get(empr_codi=obj.cont_empr).empr_nome
        except Empresas.DoesNotExist:
            logger.warning(f"Empresa com ID {obj.cont_empr} não encontrada.")
            return None

    def get_produto_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None
        try:
            produto = Produtos.objects.using(banco).filter(
                prod_codi=obj.cont_prod,
                prod_empr=obj.cont_empr
            ).first()
            return produto.prod_nome if produto else None
        except Exception as e:
            logger.warning(f"Erro ao buscar nome do produto: {e}")
            return None