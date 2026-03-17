from rest_framework import serializers

from ..models import Ncm


class NcmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ncm
        fields = ["ncm_codi", "ncm_desc"]

    def validate_ncm_codi(self, value):
        codigo = (value or "").strip()
        if not codigo:
            raise serializers.ValidationError("Informe o código NCM.")
        if len(codigo) > 10:
            raise serializers.ValidationError("Código NCM deve ter até 10 caracteres.")
        return codigo

    def create(self, validated_data):
        db_alias = self.context.get("ncm_db") or self.context.get("banco") or "default"
        return Ncm.objects.using(db_alias).create(**validated_data)

    def update(self, instance, validated_data):
        db_alias = self.context.get("ncm_db") or self.context.get("banco") or "default"
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save(using=db_alias)
        return instance
