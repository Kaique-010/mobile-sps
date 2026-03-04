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


class SafeDateField(serializers.DateField):
    def to_representation(self, value):
        try:
            return super().to_representation(value)
        except Exception:
            return None

    def get_attribute(self, instance):
        try:
            # Tenta buscar o campo seguro injetado pela view (ex: safe_orde_data_aber)
            safe_field = f"safe_{self.source_attrs[-1]}"
            if hasattr(instance, safe_field):
                val = getattr(instance, safe_field)
                if val:
                    return val
            
            return super().get_attribute(instance)
        except (ValueError, TypeError, Exception):
            return None


class SafeDateTimeField(serializers.DateTimeField):
    def to_representation(self, value):
        try:
            return super().to_representation(value)
        except Exception:
            return None

    def get_attribute(self, instance):
        try:
            # Tenta buscar o campo seguro injetado pela view
            safe_field = f"safe_{self.source_attrs[-1]}"
            if hasattr(instance, safe_field):
                val = getattr(instance, safe_field)
                if val:
                    return val

            return super().get_attribute(instance)
        except (ValueError, TypeError, Exception):
            return None


class SafeTimeField(serializers.TimeField):
    def to_representation(self, value):
        try:
            return super().to_representation(value)
        except Exception:
            return None

    def get_attribute(self, instance):
        try:
            # Tenta buscar o campo seguro injetado pela view
            safe_field = f"safe_{self.source_attrs[-1]}"
            if hasattr(instance, safe_field):
                val = getattr(instance, safe_field)
                if val:
                    return val

            return super().get_attribute(instance)
        except (ValueError, TypeError, Exception):
            return None
