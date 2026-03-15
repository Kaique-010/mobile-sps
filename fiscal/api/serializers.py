from rest_framework import serializers

from fiscal.models import NFeDocumento


class ImportarXMLSerializer(serializers.Serializer):
    empresa = serializers.IntegerField()
    filial = serializers.IntegerField()
    xml = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    chave = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        xml = (attrs.get("xml") or "").strip()
        chave = (attrs.get("chave") or "").strip()
        if not xml and not chave:
            raise serializers.ValidationError("Informe 'xml' ou 'chave'.")
        return attrs


class GerarDevolucaoSerializer(serializers.Serializer):
    empresa = serializers.IntegerField()
    filial = serializers.IntegerField()
    documento_id = serializers.IntegerField()
    emitir = serializers.BooleanField(required=False, default=False)


class NFeDocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = NFeDocumento
        fields = ("id", "empresa", "filial", "chave", "tipo", "criado_em", "atualizado_em")
