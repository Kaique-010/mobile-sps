from rest_framework import serializers

from core.serializers import BancoContextMixin
from transportes.models import Bombas
from transportes.services.bombas import BombasService


class BombasSerializer(BancoContextMixin, serializers.ModelSerializer):
    empresa_id = serializers.IntegerField(source="bomb_empr", read_only=True)
    codigo = serializers.CharField(source="bomb_codi", read_only=True)

    descricao = serializers.CharField(source="bomb_desc", required=False, allow_blank=True, allow_null=True)
    centro_custo_id = serializers.IntegerField(source="bomb_cecu", required=False, allow_null=True)
    fornecedor_id = serializers.IntegerField(source="bomb_forn", required=False, allow_null=True)
    observacoes = serializers.CharField(source="bomb_obse", required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Bombas
        fields = [
            "empresa_id",
            "codigo",
            "descricao",
            "centro_custo_id",
            "fornecedor_id",
            "observacoes",
        ]

    def create(self, validated_data):
        banco = self.get_banco()
        empresa_id = self.context.get("empresa_id")
        if not empresa_id:
            raise serializers.ValidationError({"empresa_id": "Empresa não identificada na sessão."})

        sequencial = BombasService.gerar_sequencial(empresa_id=int(empresa_id), using=banco)
        validated_data["bomb_empr"] = int(empresa_id)
        validated_data["bomb_codi"] = str(sequencial)
        return Bombas.objects.using(banco).create(**validated_data)

    def update(self, instance, validated_data):
        banco = self.get_banco()
        Bombas.objects.using(banco).filter(
            bomb_empr=instance.bomb_empr,
            bomb_codi=instance.bomb_codi,
        ).update(**validated_data)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        return instance

