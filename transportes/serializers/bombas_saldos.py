from rest_framework import serializers

from transportes.models import BombasSaldos
from transportes.services.bombas_saldos import BombasSaldosService


class BombasSaldosSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="bomb_id", read_only=True)
    empresa_id = serializers.IntegerField(source="bomb_empr", read_only=True)
    filial_id = serializers.IntegerField(source="bomb_fili", read_only=True)

    bomba_codigo = serializers.CharField(source="bomb_bomb")
    combustivel_codigo = serializers.CharField(source="bomb_comb")
    tipo_movimentacao = serializers.IntegerField(source="bomb_tipo_movi")
    quantidade = serializers.DecimalField(source="bomb_sald", max_digits=15, decimal_places=4)
    data = serializers.DateField(source="bomb_data")

    saldo_atual = serializers.SerializerMethodField()
    saldo_depois = serializers.SerializerMethodField()

    class Meta:
        model = BombasSaldos
        fields = [
            "id",
            "empresa_id",
            "filial_id",
            "bomba_codigo",
            "combustivel_codigo",
            "tipo_movimentacao",
            "quantidade",
            "data",
            "saldo_atual",
            "saldo_depois",
        ]

    def get_saldo_atual(self, obj):
        return getattr(obj, "saldo_atual", None)

    def get_saldo_depois(self, obj):
        return getattr(obj, "saldo_depois", None)

    def create(self, validated_data):
        banco = self.context["banco"]
        empresa_id = self.context.get("empresa_id")
        filial_id = self.context.get("filial_id") or 1
        usuario_id = self.context.get("usuario_id")

        mov, saldo_atual, saldo_depois = BombasSaldosService.registrar_movimentacao(
            using=banco,
            empresa_id=int(empresa_id),
            filial_id=int(filial_id),
            bomb_bomb=validated_data["bomb_bomb"],
            bomb_comb=validated_data["bomb_comb"],
            tipo_movi=int(validated_data["bomb_tipo_movi"]),
            quantidade=validated_data["bomb_sald"],
            data=validated_data["bomb_data"],
            usuario_id=usuario_id,
        )
        mov.saldo_atual = saldo_atual
        mov.saldo_depois = saldo_depois
        return mov

    def update(self, instance, validated_data):
        banco = self.context["banco"]
        empresa_id = self.context.get("empresa_id")
        filial_id = self.context.get("filial_id") or 1
        usuario_id = self.context.get("usuario_id")

        mov, saldo_atual, saldo_depois = BombasSaldosService.atualizar_movimentacao(
            using=banco,
            empresa_id=int(empresa_id),
            filial_id=int(filial_id),
            bomb_id=int(instance.bomb_id),
            bomb_bomb=validated_data.get("bomb_bomb", instance.bomb_bomb),
            bomb_comb=validated_data.get("bomb_comb", instance.bomb_comb),
            tipo_movi=int(validated_data.get("bomb_tipo_movi", instance.bomb_tipo_movi)),
            quantidade=validated_data.get("bomb_sald", instance.bomb_sald),
            data=validated_data.get("bomb_data", instance.bomb_data),
            usuario_id=usuario_id,
        )
        mov.saldo_atual = saldo_atual
        mov.saldo_depois = saldo_depois
        return mov
