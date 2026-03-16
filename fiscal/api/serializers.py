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


class NFeDocumentoDetailSerializer(serializers.ModelSerializer):
    ide = serializers.SerializerMethodField()
    emitente = serializers.SerializerMethodField()
    destinatario = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    itens = serializers.SerializerMethodField()

    class Meta:
        model = NFeDocumento
        fields = (
            "id",
            "empresa",
            "filial",
            "chave",
            "tipo",
            "criado_em",
            "atualizado_em",
            "ide",
            "emitente",
            "destinatario",
            "total",
            "itens",
        )

    def _to_decimal(self, value):
        from decimal import Decimal, InvalidOperation

        if value is None:
            return Decimal("0")
        try:
            s = str(value).strip().replace(",", ".")
            if not s:
                return Decimal("0")
            return Decimal(s)
        except (InvalidOperation, ValueError):
            return Decimal("0")

    def get_ide(self, obj: NFeDocumento):
        data = obj.json_dict or {}
        return data.get("ide") or {}

    def get_emitente(self, obj: NFeDocumento):
        data = obj.json_dict or {}
        return data.get("emitente") or {}

    def get_destinatario(self, obj: NFeDocumento):
        data = obj.json_dict or {}
        return data.get("destinatario") or {}

    def get_total(self, obj: NFeDocumento):
        data = obj.json_dict or {}
        return data.get("total") or {}

    def get_itens(self, obj: NFeDocumento):
        data = obj.json_dict or {}
        itens = data.get("itens") or []
        if not isinstance(itens, list):
            return []

        out = []
        for item in itens:
            if not isinstance(item, dict):
                continue

            q = self._to_decimal(item.get("qCom"))
            unit = self._to_decimal(item.get("vUnCom"))
            v_prod = self._to_decimal(item.get("vProd"))
            v_desc = self._to_decimal(item.get("vDesc"))
            v_liq = v_prod - v_desc

            out.append(
                {
                    "nItem": str(item.get("nItem") or "").strip(),
                    "cProd": str(item.get("cProd") or "").strip(),
                    "cEAN": str(item.get("cEAN") or "").strip(),
                    "xProd": str(item.get("xProd") or "").strip(),
                    "NCM": str(item.get("NCM") or "").strip(),
                    "CFOP": str(item.get("CFOP") or "").strip(),
                    "CEST": str(item.get("CEST") or "").strip(),
                    "uCom": str(item.get("uCom") or "").strip(),
                    "qCom": str(q),
                    "vUnCom": str(unit),
                    "vProd": str(v_prod),
                    "vDesc": str(v_desc),
                    "vLiquido": str(v_liq),
                }
            )
        return out
