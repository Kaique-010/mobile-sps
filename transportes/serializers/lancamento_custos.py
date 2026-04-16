from rest_framework import serializers

from transportes.services.servico_de_lancamento_custos import LancamentoCustosService


class LancamentoCustosSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    empresa_id = serializers.IntegerField(read_only=True)
    filial_id = serializers.IntegerField(read_only=True)

    data = serializers.DateField(source="lacu_data", required=False, allow_null=True)
    frota_id = serializers.CharField(source="lacu_frot", required=False, allow_blank=True, allow_null=True)
    veiculo_id = serializers.IntegerField(source="lacu_veic", required=False, allow_null=True)
    motorista_id = serializers.IntegerField(source="lacu_moto", required=False, allow_null=True)
    entidade_id = serializers.IntegerField(source="lacu_forn", required=False, allow_null=True)
    entidade_nome = serializers.CharField(source="lacu_nome_forn", read_only=True)
    item_codigo = serializers.CharField(source="lacu_item", required=False, allow_blank=True, allow_null=True)
    item_descricao = serializers.CharField(source="lacu_nome_item", required=False, allow_blank=True, allow_null=True)
    documento = serializers.CharField(source="lacu_docu", required=False, allow_blank=True, allow_null=True)
    quantidade = serializers.DecimalField(source="lacu_quan", max_digits=15, decimal_places=5, required=False, allow_null=True)
    valor_unitario = serializers.DecimalField(source="lacu_unit", max_digits=15, decimal_places=4, required=False, allow_null=True)
    total = serializers.DecimalField(source="lacu_tota", max_digits=15, decimal_places=2, read_only=True)
    nota_fiscal = serializers.DecimalField(source="lacu_nota", max_digits=9, decimal_places=0, required=False, allow_null=True)
    cupom = serializers.DecimalField(source="lacu_cupo", max_digits=9, decimal_places=0, required=False, allow_null=True)
    observacoes = serializers.CharField(source="lacu_obse", required=False, allow_blank=True, allow_null=True)

    def _payload_from_validated(self, validated_data):
        empresa_id = self.context.get("empresa_id")
        filial_id = self.context.get("filial_id")
        instance = getattr(self, "instance", None)

        def current(field_name):
            if field_name in validated_data:
                return validated_data.get(field_name)
            if instance is not None:
                return getattr(instance, field_name, None)
            return None

        return {
            "lacu_empr": empresa_id,
            "lacu_fili": filial_id,
            "lacu_data": current("lacu_data"),
            "lacu_frot": current("lacu_frot"),
            "lacu_veic": current("lacu_veic"),
            "lacu_moto": current("lacu_moto"),
            "lacu_forn": current("lacu_forn"),
            "lacu_nome_forn": current("lacu_nome_forn"),
            "lacu_item": current("lacu_item"),
            "lacu_nome_item": current("lacu_nome_item"),
            "lacu_docu": current("lacu_docu"),
            "lacu_quan": current("lacu_quan"),
            "lacu_unit": current("lacu_unit"),
            "lacu_nota": current("lacu_nota"),
            "lacu_cupo": current("lacu_cupo"),
            "lacu_obse": current("lacu_obse"),
        }

    def validate(self, attrs):
        banco = self.context.get("banco")
        if not banco:
            raise serializers.ValidationError("Banco não definido no contexto.")
        if not self.context.get("empresa_id"):
            raise serializers.ValidationError("Empresa não identificada na sessão.")
        if not self.context.get("filial_id"):
            raise serializers.ValidationError("Filial não identificada na sessão.")

        payload = self._payload_from_validated(attrs)
        try:
            LancamentoCustosService.validar_dados(payload, using=banco)
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)})

        attrs["_service_payload"] = payload
        return attrs

    def create(self, validated_data):
        banco = self.context["banco"]
        usuario_id = self.context.get("usuario_id")
        payload = validated_data.pop("_service_payload", self._payload_from_validated(validated_data))
        try:
            return LancamentoCustosService.create_custo(payload, user_id=usuario_id, using=banco)
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)})

    def update(self, instance, validated_data):
        banco = self.context["banco"]
        usuario_id = self.context.get("usuario_id")
        payload = validated_data.pop("_service_payload", self._payload_from_validated(validated_data))
        try:
            return LancamentoCustosService.update_custo(instance, payload, user_id=usuario_id, using=banco)
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)})

    def to_representation(self, instance):
        return {
            "id": instance.lacu_ctrl,
            "empresa_id": instance.lacu_empr,
            "filial_id": instance.lacu_fili,
            "data": instance.lacu_data,
            "frota_id": instance.lacu_frot,
            "veiculo_id": instance.lacu_veic,
            "motorista_id": instance.lacu_moto,
            "entidade_id": instance.lacu_forn,
            "entidade_nome": getattr(instance, "lacu_nome_forn", None),
            "item_codigo": instance.lacu_item,
            "item_descricao": instance.lacu_nome_item,
            "documento": instance.lacu_docu,
            "quantidade": instance.lacu_quan,
            "valor_unitario": instance.lacu_unit,
            "total": instance.lacu_tota,
            "nota_fiscal": instance.lacu_nota,
            "cupom": instance.lacu_cupo,
            "observacoes": instance.lacu_obse,
        }
