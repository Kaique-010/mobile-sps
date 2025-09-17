from rest_framework import serializers
from .models import Lctobancario
from rest_framework.exceptions import ValidationError
from django.db import models
from django.db.models import Max
from .utils import get_next_lcto_number
from Licencas.models import Empresas
from core.serializers import BancoContextMixin


class LctobancarioSerializer(BancoContextMixin, serializers.ModelSerializer):
    laba_ctrl = serializers.IntegerField(required=False, read_only=True)
    class Meta:
        model = Lctobancario
        fields = 'laba_empr', 'laba_fili', 'laba_banc',
        'laba_data', 'laba_cecu','laba_valo','laba_hist',
        'laba_dcbr', 'laba_enti',

    def create(self, validated_data):
        banco = self.context.get('banco')
        lcto_ctrl = get_next_lcto_number(
            validated_data['laba_empr'],
            validated_data['laba_fili'],
            banco
        )
        validated_data['laba_ctrl'] = lcto_ctrl
        return Lctobancario.objects.using(banco).create(**validated_data)
    
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
