from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Propriedades
from core.serializers import BancoContextMixin
from Licencas.models import Empresas
from .utils import get_next_prop_number

import logging

logger = logging.getLogger(__name__)


class PropriedadesSerializer(BancoContextMixin, serializers.ModelSerializer):
    empresa_nome = serializers.SerializerMethodField(read_only=True)
    prop_codi = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Propriedades
        fields = '__all__'
    
    def validate(self, attrs):
        """Validações customizadas"""
        prop_hect = attrs.get('prop_hect')
        if prop_hect is not None and prop_hect < 0:
            raise ValidationError({"prop_hect": "Hectares não pode ser negativo."})
        
        return attrs
    
    def get_empresa_nome(self, obj):
        """Retorna o nome da empresa"""
        banco = self.context.get('banco')
        if not banco:
            return None
        
        try:
            return Empresas.objects.using(banco).get(empr_codi=obj.prop_empr).empr_nome
        except Empresas.DoesNotExist:
            logger.warning(f"Empresa com ID {obj.prop_empr} não encontrada.")
            return None
    
    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")
        
        # Gera próximo código se não fornecido
        if not validated_data.get('prop_codi'):
            validated_data['prop_codi'] = get_next_prop_number(
                validated_data['prop_empr'], 
                validated_data['prop_fili'], 
                banco
            )
        
        return Propriedades.objects.using(banco).create(**validated_data)
