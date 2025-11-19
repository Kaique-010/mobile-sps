# notas_fiscais/serializers.py

from rest_framework import serializers
from ..models import (
    Nota, NotaItem, NotaItemImposto,
    Transporte
)
from Entidades.models import Entidades
from Licencas.models import Filiais


# ============================================================
# PARTICIPANTES (LEITURA)
# ============================================================

class DestinatarioResumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Entidades
        fields = ["enti_clie", "enti_nome", "enti_cnpj", "enti_cpf", "enti_emai"]


class EmitenteResumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Filiais
        fields = ["empr_empr", "empr_codi", "empr_nome", "empr_docu", "empr_cep", "empr_ende", "empr_cida", "empr_esta"]


# ============================================================
# ITENS + IMPOSTOS (LEITURA)
# ============================================================

class NotaItemImpostoSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotaItemImposto
        fields = "__all__"


class NotaItemSerializer(serializers.ModelSerializer):
    impostos = NotaItemImpostoSerializer(read_only=True)

    class Meta:
        model = NotaItem
        fields = "__all__"


# ============================================================
# TRANSPORTE (LEITURA)
# ============================================================

class TransporteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transporte
        fields = "__all__"


# ============================================================
# NOTA – LEITURA
# ============================================================

class NotaDetailSerializer(serializers.ModelSerializer):
    itens = NotaItemSerializer(many=True, read_only=True)
    transporte = TransporteSerializer(read_only=True)
    emitente = EmitenteResumoSerializer(read_only=True)
    destinatario = DestinatarioResumoSerializer(read_only=True)

    class Meta:
        model = Nota
        fields = "__all__"


# ============================================================
# NOTA – ESCRITA (API)
# ============================================================

class NotaItemCreateSerializer(serializers.Serializer):
    produto = serializers.IntegerField()
    quantidade = serializers.DecimalField(max_digits=15, decimal_places=4)
    unitario = serializers.DecimalField(max_digits=15, decimal_places=4)
    desconto = serializers.DecimalField(max_digits=15, decimal_places=4, required=False, default=0)
    cfop = serializers.CharField()
    ncm = serializers.CharField()
    cest = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    cst_icms = serializers.CharField()
    cst_pis = serializers.CharField()
    cst_cofins = serializers.CharField()


class NotaItemImpostoCreateSerializer(serializers.Serializer):
    icms_base = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, allow_null=True)
    icms_aliquota = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    icms_valor = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, allow_null=True)
    ipi_valor = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, allow_null=True)
    pis_valor = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, allow_null=True)
    cofins_valor = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, allow_null=True)
    fcp_valor = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, allow_null=True)
    ibs_base = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, allow_null=True)
    ibs_aliquota = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    ibs_valor = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, allow_null=True)
    cbs_base = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, allow_null=True)
    cbs_aliquota = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    cbs_valor = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, allow_null=True)


class TransporteCreateSerializer(serializers.Serializer):
    modalidade_frete = serializers.IntegerField()
    transportadora = serializers.IntegerField(required=False, allow_null=True)
    placa_veiculo = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    uf_veiculo = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class NotaCreateUpdateSerializer(serializers.Serializer):
    modelo = serializers.CharField()
    serie = serializers.CharField()
    numero = serializers.IntegerField()

    data_emissao = serializers.DateField(required=False)
    data_saida = serializers.DateField(required=False, allow_null=True)

    tipo_operacao = serializers.IntegerField()
    finalidade = serializers.IntegerField(required=False)
    ambiente = serializers.IntegerField(required=False)

    destinatario = serializers.IntegerField()  # enti_clie

    itens = NotaItemCreateSerializer(many=True)
    impostos = NotaItemImpostoCreateSerializer(many=True, required=False)
    transporte = TransporteCreateSerializer(required=False)

    def validate(self, attrs):
        itens = attrs.get("itens") or []
        impostos = attrs.get("impostos") or []

        if not itens:
            raise serializers.ValidationError("A nota precisa ter pelo menos um item.")

        if impostos and len(impostos) != len(itens):
            raise serializers.ValidationError("Se enviados, impostos devem ter o mesmo tamanho da lista de itens.")

        return attrs
