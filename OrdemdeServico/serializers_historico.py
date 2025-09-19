from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from core.serializers import BancoContextMixin
from .models import HistoricoWorkflow


class BancoModelSerializer(BancoContextMixin, serializers.ModelSerializer):
    """Serializer base com contexto de banco"""
    pass


class HistoricoWorkflowSerializer(BancoModelSerializer):
    """Serializer para histórico de movimentações entre setores"""
    
    class Meta:
        model = HistoricoWorkflow
        fields = '__all__'
        read_only_fields = ('hist_id', 'hist_data')
    
    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError('Banco não encontrado no contexto')
        instance = self.Meta.model.objects.using(banco).create(**validated_data)
        return instance