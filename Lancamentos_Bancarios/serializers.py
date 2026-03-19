from rest_framework import serializers
from .models import Lctobancario
from rest_framework.exceptions import ValidationError
from Licencas.models import Empresas
from core.serializers import BancoContextMixin
import logging

from .services import criar_lancamento

logger = logging.getLogger(__name__)


class LctobancarioSerializer(BancoContextMixin, serializers.ModelSerializer):
    laba_ctrl = serializers.IntegerField(required=False, read_only=True)
    class Meta:
        model = Lctobancario
        fields = ('laba_empr', 'laba_fili', 'laba_banc',
        'laba_data', 'laba_cecu','laba_valo','laba_hist',
        'laba_dbcr', 'laba_enti', 'laba_ctrl')

    def create(self, validated_data):
        banco = self.context.get('banco')
        return criar_lancamento(banco=banco, dados=validated_data)

    def update(self, instance, validated_data):
        banco = self.context.get('banco')
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=banco)
        return instance
    
    def get_empresa_nome(self, obj):
        """Retorna o nome da empresa"""
        banco = self.context.get('banco')
        if not banco:
            return None
        
        try:
            return Empresas.objects.using(banco).get(empr_codi=obj.laba_empr).empr_nome
        except Empresas.DoesNotExist:
            logger.warning(f"Empresa com ID {obj.laba_empr} não encontrada.")
            return None
