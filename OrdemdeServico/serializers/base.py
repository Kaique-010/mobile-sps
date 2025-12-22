from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from core.serializers import BancoContextMixin

class BancoModelSerializer(BancoContextMixin, serializers.ModelSerializer):
    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError('Banco não encontrado no contexto')
        instance = self.Meta.model.objects.using(banco).create(**validated_data)
        return instance

    def update(self, instance, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError('Banco não encontrado no contexto')
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=banco)
        return instance
