from rest_framework import serializers

from transportes.services.servico_de_abastecimento import AbastecimentoService


class AbastecimentoSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    empresa_id = serializers.IntegerField(read_only=True)
    filial_id = serializers.IntegerField(read_only=True)

    data = serializers.DateField(source="abas_data", required=False, allow_null=True)
    frota_id = serializers.CharField(source="abas_frot", required=False, allow_blank=True, allow_null=True)
    veiculo_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    funcionario_id = serializers.IntegerField(source="abas_func", required=False, allow_null=True)
    fornecedor_id = serializers.IntegerField(source="abas_enti", required=False, allow_null=True)
    bomba_codigo = serializers.CharField(source="abas_bomb", required=False, allow_blank=True, allow_null=True)
    combustivel_codigo = serializers.CharField(source="abas_comb", required=False, allow_blank=True, allow_null=True)
    quantidade = serializers.DecimalField(source="abas_quan", max_digits=15, decimal_places=4, required=False, allow_null=True)
    valor_unitario = serializers.DecimalField(source="abas_unit", max_digits=15, decimal_places=4, required=False, allow_null=True)
    total = serializers.DecimalField(source="abas_tota", max_digits=15, decimal_places=2, read_only=True)
    horimetro_atual = serializers.DecimalField(source="abas_hokm", max_digits=15, decimal_places=2, required=False, allow_null=True)
    horimetro_anterior = serializers.DecimalField(source="abas_hokm_ante", max_digits=15, decimal_places=2, required=False, allow_null=True)
    observacoes = serializers.CharField(source="abas_obse", required=False, allow_blank=True, allow_null=True)

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

        payload = {
            "abas_empr": empresa_id,
            "abas_fili": filial_id,
            "abas_data": current("abas_data"),
            "abas_frot": current("abas_frot"),
            "abas_veic_sequ": validated_data.get("veiculo_id"),
            "abas_func": current("abas_func"),
            "abas_enti": current("abas_enti"),
            "abas_bomb": current("abas_bomb"),
            "abas_comb": current("abas_comb"),
            "abas_quan": current("abas_quan"),
            "abas_unit": current("abas_unit"),
            "abas_hokm": current("abas_hokm"),
            "abas_hokm_ante": current("abas_hokm_ante"),
            "abas_obse": current("abas_obse"),
        }
        return payload

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
            AbastecimentoService.validar_dados(payload, using=banco)
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)})

        attrs["_service_payload"] = payload
        return attrs

    def create(self, validated_data):
        banco = self.context["banco"]
        usuario_id = self.context.get("usuario_id")
        payload = validated_data.pop("_service_payload", self._payload_from_validated(validated_data))
        try:
            return AbastecimentoService.create_abastecimento(payload, user_id=usuario_id, using=banco)
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)})

    def update(self, instance, validated_data):
        banco = self.context["banco"]
        usuario_id = self.context.get("usuario_id")
        payload = validated_data.pop("_service_payload", self._payload_from_validated(validated_data))
        try:
            return AbastecimentoService.update_abastecimento(instance, payload, user_id=usuario_id, using=banco)
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)})

    def to_representation(self, instance):
        return {
            "id": instance.abas_ctrl,
            "empresa_id": instance.abas_empr,
            "filial_id": instance.abas_fili,
            "data": instance.abas_data,
            "frota_id": instance.abas_frot,
            "funcionario_id": instance.abas_func,
            "fornecedor_id": instance.abas_enti,
            "bomba_codigo": instance.abas_bomb,
            "combustivel_codigo": instance.abas_comb,
            "quantidade": instance.abas_quan,
            "valor_unitario": instance.abas_unit,
            "total": instance.abas_tota,
            "horimetro_atual": instance.abas_hokm,
            "horimetro_anterior": instance.abas_hokm_ante,
            "observacoes": instance.abas_obse,
        }

