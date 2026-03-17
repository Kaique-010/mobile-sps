from rest_framework import serializers

from ..models import CFOP


class CFOPSerializer(serializers.ModelSerializer):
    CAMPOS_PADRAO = [
        "cfop_empr",
        "cfop_codi",
        "cfop_desc",
    ]

    INCIDENCIAS = [
        "cfop_exig_ipi",
        "cfop_exig_icms",
        "cfop_exig_pis_cofins",
        "cfop_exig_cbs",
        "cfop_exig_ibs",
        "cfop_gera_st",
        "cfop_gera_difal",
        "cfop_icms_base_inclui_ipi",
        "cfop_st_base_inclui_ipi",
        "cfop_ipi_tota_nf",
        "cfop_st_tota_nf",
    ]

    class Meta:
        model = CFOP
        fields = [
            "cfop_id",
            "cfop_empr",
            "cfop_codi",
            "cfop_desc",
            "cfop_exig_ipi",
            "cfop_exig_icms",
            "cfop_exig_pis_cofins",
            "cfop_exig_cbs",
            "cfop_exig_ibs",
            "cfop_gera_st",
            "cfop_gera_difal",
            "cfop_icms_base_inclui_ipi",
            "cfop_st_base_inclui_ipi",
            "cfop_ipi_tota_nf",
            "cfop_st_tota_nf",
        ]
        extra_kwargs = {
            "cfop_empr": {"required": False},
        }

    def to_internal_value(self, data):
        if isinstance(data, dict) and ("campos_padrao" in data or "incidencias" in data):
            flat = {}

            for k, v in data.items():
                if k in self.fields:
                    flat[k] = v

            for item in data.get("campos_padrao") or []:
                if not isinstance(item, dict):
                    continue
                campo = item.get("campo")
                if campo in self.CAMPOS_PADRAO:
                    flat[campo] = item.get("valor")

            bool_field = serializers.BooleanField()
            for item in data.get("incidencias") or []:
                if not isinstance(item, dict):
                    continue
                campo = item.get("campo")
                if campo in self.INCIDENCIAS:
                    flat[campo] = bool_field.to_internal_value(item.get("valor"))

            return super().to_internal_value(flat)

        return super().to_internal_value(data)

    def to_representation(self, instance):
        def montar_item(field_name: str):
            field = instance._meta.get_field(field_name)
            return {
                "campo": field_name,
                "valor": getattr(instance, field_name),
                "label": str(getattr(field, "verbose_name", field_name)),
                "help_text": str(getattr(field, "help_text", "")) or "",
            }

        return {
            "cfop_id": instance.cfop_id,
            "campos_padrao": [montar_item(f) for f in self.CAMPOS_PADRAO],
            "incidencias": [montar_item(f) for f in self.INCIDENCIAS],
        }

