from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from Entidades.models import Entidades
from conciliacao.models import ConciliacaoBancaria, ItemExtrato


class ConciliacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConciliacaoBancaria
        fields = ("nume", "empresa", "filial", "codigo_banco", "data")
        read_only_fields = fields


class ItemExtratoSerializer(serializers.ModelSerializer):
    valor = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
        coerce_to_string=True,
        allow_null=True,
        read_only=True,
    )

    class Meta:
        model = ItemExtrato
        fields = (
            "id", "nume", "empresa", "filial", "documento", "data_operacao",
            "tipo", "valor", "historico", "existe", "selecionado", "linha",
        )
        read_only_fields = fields


class EscopoSerializer(serializers.Serializer):
    empresa = serializers.IntegerField(min_value=1, required=False)
    filial = serializers.IntegerField(min_value=1, required=False)

    def validate(self, attrs):
        ctx = self.context["ctx"]
        for campo in ("empresa", "filial"):
            if campo in attrs and attrs[campo] != getattr(ctx, campo):
                raise PermissionDenied(
                    "Empresa e filial devem corresponder ao contexto autenticado."
                )
        return attrs


class ConciliacaoFiltroSerializer(EscopoSerializer):
    codigo_banco = serializers.IntegerField(min_value=1, required=False)
    data = serializers.DateField(required=False)
    numero = serializers.IntegerField(min_value=1, required=False)



class ImportarOFXSerializer(serializers.Serializer):
    codigo_banco = serializers.IntegerField(min_value=1)
    arquivo = serializers.FileField()

    def validate(self, attrs):
        ctx = self.context["ctx"]

        banco_existe = Entidades.objects.using(
            ctx.db_alias
        ).filter(
            enti_empr=ctx.empresa,
            enti_clie=attrs["codigo_banco"],
            enti_tien="B",
        ).exists()

        if not banco_existe:
            raise serializers.ValidationError({
                "codigo_banco": (
                    "Banco não encontrado para a empresa autenticada."
                )
            })

        return attrs