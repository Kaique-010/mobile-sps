import re

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from core.serializers import BancoContextMixin
from transportes.models import Mdfe, MdfeDocumento


class MdfeSerializer(BancoContextMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(source="mdf_id", read_only=True)
    empresa_id = serializers.IntegerField(source="mdf_empr", read_only=True)
    filial_id = serializers.IntegerField(source="mdf_fili", read_only=True)

    numero = serializers.IntegerField(source="mdf_nume", read_only=True)
    serie = serializers.IntegerField(source="mdf_seri", required=False, allow_null=True)
    emissao = serializers.DateField(source="mdf_emis", required=False, allow_null=True)

    chave = serializers.CharField(source="mdf_chav", read_only=True)
    xml = serializers.CharField(source="mdf_xml_mdf", read_only=True)

    uf_origem = serializers.CharField(source="mdf_esta_orig", required=False, allow_blank=True, allow_null=True)
    uf_destino = serializers.CharField(source="mdf_esta_dest", required=False, allow_blank=True, allow_null=True)

    municipio_carregamento_id = serializers.CharField(source="mdf_cida_carr", required=False, allow_blank=True, allow_null=True)
    municipio_carregamento_nome = serializers.CharField(source="mdf_nome_carr", required=False, allow_blank=True, allow_null=True)

    tipo_emitente = serializers.CharField(source="mdf_tipo_emit", required=False, allow_blank=True, allow_null=True)
    tipo_transportador = serializers.IntegerField(source="mdf_tipo_tran", required=False, allow_null=True)
    tipo_carga = serializers.CharField(source="mdf_pred_carg", required=False, allow_blank=True, allow_null=True)

    produto_descricao = serializers.CharField(source="mdf_pred_xprod", required=False, allow_blank=True, allow_null=True)
    produto_ncm = serializers.CharField(source="mdf_pred_ncm", required=False, allow_blank=True, allow_null=True)
    produto_ean = serializers.CharField(source="mdf_pred_ean", required=False, allow_blank=True, allow_null=True)

    transportadora_id = serializers.IntegerField(source="mdf_tran", required=False, allow_null=True)
    motorista_id = serializers.IntegerField(source="mdf_moto", required=False, allow_null=True)
    veiculo_id = serializers.IntegerField(source="mdf_veic", required=False, allow_null=True)

    status = serializers.IntegerField(source="mdf_stat", read_only=True)
    cancelado = serializers.BooleanField(source="mdf_canc", read_only=True)
    finalizado = serializers.BooleanField(source="mdf_fina", read_only=True)

    class Meta:
        model = Mdfe
        fields = [
            "id",
            "empresa_id",
            "filial_id",
            "numero",
            "serie",
            "emissao",
            "chave",
            "xml",
            "uf_origem",
            "uf_destino",
            "municipio_carregamento_id",
            "municipio_carregamento_nome",
            "tipo_emitente",
            "tipo_transportador",
            "tipo_carga",
            "produto_descricao",
            "produto_ncm",
            "produto_ean",
            "transportadora_id",
            "motorista_id",
            "veiculo_id",
            "status",
            "cancelado",
            "finalizado",
        ]

    def create(self, validated_data):
        banco = self.get_banco()
        return Mdfe.objects.using(banco).create(**validated_data)

    def update(self, instance, validated_data):
        banco = self.get_banco()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=banco)
        return instance


class MdfeDocumentoSerializer(BancoContextMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class TipoDocField(serializers.Field):
        def to_representation(self, value):
            return "CTe" if str(value or "00") == "01" else "NFe"

        def to_internal_value(self, data):
            val = str(data or "").strip()
            if val in ("NFe", "00"):
                return "00"
            if val in ("CTe", "01"):
                return "01"
            raise ValidationError("Tipo inválido. Use 'NFe' ou 'CTe'.")

    tipo = TipoDocField(source="tipo_doc")
    chave = serializers.CharField(required=True, allow_blank=False)
    municipio_descarga_id = serializers.CharField(source="cmun_descarga", required=False, allow_blank=True, allow_null=True)
    municipio_descarga_nome = serializers.CharField(source="xmun_descarga", required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = MdfeDocumento
        fields = [
            "id",
            "tipo",
            "chave",
            "municipio_descarga_id",
            "municipio_descarga_nome",
        ]

    def validate_chave(self, value):
        chave = re.sub(r"\D", "", str(value or ""))
        if len(chave) != 44 or not chave.isdigit():
            raise ValidationError("A chave deve conter 44 dígitos numéricos.")

        soma = 0
        peso = 2
        for digito in reversed(chave[:43]):
            soma += int(digito) * peso
            peso += 1
            if peso > 9:
                peso = 2
        resto = soma % 11
        dv_calc = 0 if resto < 2 else 11 - resto
        if str(dv_calc) != chave[-1]:
            raise ValidationError("Chave com DV inválido.")

        return chave
