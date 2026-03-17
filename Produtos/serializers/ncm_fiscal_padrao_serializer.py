from django.db.models import F, Value
from django.db.models.functions import Replace
from rest_framework import serializers

from CFOP.models import NcmFiscalPadrao
from Produtos.models import Ncm


class NcmFiscalPadraoSerializer(serializers.ModelSerializer):
    ncm = serializers.SerializerMethodField()
    ncm_codigo = serializers.CharField(write_only=True, required=False, allow_blank=False)
    ncm_id = serializers.CharField(read_only=True)

    class Meta:
        model = NcmFiscalPadrao
        fields = [
            "id",
            "ncm",
            "ncm_codigo",
            "ncm_id",
            "cfop",
            "uf_origem",
            "uf_destino",
            "tipo_entidade",
            "cst_icms",
            "aliq_icms",
            "cst_ipi",
            "aliq_ipi",
            "cst_pis",
            "aliq_pis",
            "cst_cofins",
            "aliq_cofins",
            "cst_cbs",
            "aliq_cbs",
            "cst_ibs",
            "aliq_ibs",
        ]
        extra_kwargs = {
            "cfop": {"required": False, "allow_null": True, "allow_blank": True},
            "uf_origem": {"required": False, "allow_null": True, "allow_blank": True},
            "uf_destino": {"required": False, "allow_null": True, "allow_blank": True},
            "tipo_entidade": {"required": False, "allow_null": True, "allow_blank": True},
            "cst_icms": {"required": False, "allow_null": True, "allow_blank": True},
            "cst_ipi": {"required": False, "allow_null": True, "allow_blank": True},
            "cst_pis": {"required": False, "allow_null": True, "allow_blank": True},
            "cst_cofins": {"required": False, "allow_null": True, "allow_blank": True},
            "cst_cbs": {"required": False, "allow_null": True, "allow_blank": True},
            "cst_ibs": {"required": False, "allow_null": True, "allow_blank": True},
            "aliq_icms": {"required": False, "allow_null": True},
            "aliq_ipi": {"required": False, "allow_null": True},
            "aliq_pis": {"required": False, "allow_null": True},
            "aliq_cofins": {"required": False, "allow_null": True},
            "aliq_cbs": {"required": False, "allow_null": True},
            "aliq_ibs": {"required": False, "allow_null": True},
        }

    def _get_banco(self):
        return self.context.get("banco") or "default"

    def _get_ncm_db(self):
        return self.context.get("ncm_db") or self._get_banco()

    def _normalize_ncm_candidates(self, raw_value):
        raw = str(raw_value).split(" - ")[0].strip()
        digits = "".join(ch for ch in raw if ch.isdigit())

        candidates = []
        for c in (raw, digits):
            c = (c or "").strip()
            if c and c not in candidates:
                candidates.append(c)

        if digits and len(digits) == 8:
            dotted = f"{digits[:4]}.{digits[4:6]}.{digits[6:]}"
            if dotted not in candidates:
                candidates.insert(1, dotted)

        if raw and "." in raw:
            no_dots = raw.replace(".", "").strip()
            if no_dots and no_dots not in candidates:
                candidates.append(no_dots)

        return raw, digits, candidates

    def _buscar_ncm(self, raw_value):
        raw, digits, candidates = self._normalize_ncm_candidates(raw_value)
        search_dbs = [self._get_ncm_db()]
        banco = self._get_banco()
        if banco and banco not in search_dbs:
            search_dbs.append(banco)

        obj = None
        for db_alias in search_dbs:
            for code in candidates:
                obj = Ncm.objects.using(db_alias).filter(ncm_codi=code).first()
                if obj:
                    return obj, obj.ncm_codi

        if digits:
            for db_alias in search_dbs:
                obj = (
                    Ncm.objects.using(db_alias)
                    .annotate(
                        _ncm_norm=Replace(
                            Replace(F("ncm_codi"), Value("."), Value("")),
                            Value(" "),
                            Value(""),
                        )
                    )
                    .filter(_ncm_norm=digits)
                    .first()
                )
                if obj:
                    return obj, obj.ncm_codi

        raise serializers.ValidationError(f"NCM '{raw}' não encontrado.")

    def validate_cfop(self, value):
        if value is None:
            return None
        raw = str(value).strip()
        if not raw:
            return None
        raw = raw.split(" - ")[0].strip()
        digits = "".join(ch for ch in raw if ch.isdigit())
        if len(digits) != 4:
            raise serializers.ValidationError("CFOP deve conter 4 dígitos.")
        return digits

    def validate_ncm_codigo(self, value):
        if value is None:
            return None
        raw = str(value).strip()
        if not raw:
            return None
        _, code = self._buscar_ncm(raw)
        return code

    def validate(self, attrs):
        if not attrs.get("ncm_codigo") and hasattr(self, "initial_data"):
            raw_candidates = []

            def _push(v):
                if v is None:
                    return
                if isinstance(v, dict):
                    v = v.get("codigo") or v.get("ncm_codi") or v.get("value")
                if v is None:
                    return
                s = str(v).strip()
                if not s:
                    return
                if s not in raw_candidates:
                    raw_candidates.append(s)

            data = self.initial_data

            _push(data.get("ncm_codigo"))
            _push(data.get("ncm_codi"))
            _push(data.get("ncm_id"))
            _push(data.get("ncm"))

            picked = None
            for c in raw_candidates:
                digits = "".join(ch for ch in c if ch.isdigit())
                if digits:
                    picked = c
                    break

            if picked is not None:
                try:
                    _, code = self._buscar_ncm(picked)
                except serializers.ValidationError as e:
                    raise serializers.ValidationError({"ncm_codigo": e.detail})
                attrs["ncm_codigo"] = code

        if self.instance is None and not attrs.get("ncm_codigo"):
            raise serializers.ValidationError({"ncm_codigo": "Informe o NCM."})
        return attrs

    def get_ncm(self, obj):
        code = getattr(obj, "ncm_id", None) or getattr(getattr(obj, "ncm", None), "ncm_codi", None)
        if not code:
            return None
        ncm_map = self.context.get("ncm_map") or {}
        cached = ncm_map.get(code)
        if cached is not None:
            return cached

        ncm_obj = Ncm.objects.using(self._get_ncm_db()).filter(ncm_codi=code).first()
        if not ncm_obj:
            banco = self._get_banco()
            if banco != self._get_ncm_db():
                ncm_obj = Ncm.objects.using(banco).filter(ncm_codi=code).first()
        if not ncm_obj:
            return {"codigo": code, "descricao": None}
        return {"codigo": ncm_obj.ncm_codi, "descricao": ncm_obj.ncm_desc}

    def create(self, validated_data):
        banco = self._get_banco()
        ncm_codigo = validated_data.pop("ncm_codigo", None)
        if ncm_codigo:
            validated_data["ncm_id"] = ncm_codigo
        return NcmFiscalPadrao.objects.using(banco).create(**validated_data)

    def update(self, instance, validated_data):
        banco = self._get_banco()
        ncm_codigo = validated_data.pop("ncm_codigo", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        if ncm_codigo:
            setattr(instance, "ncm_id", ncm_codigo)
        instance.save(using=banco)
        return instance
