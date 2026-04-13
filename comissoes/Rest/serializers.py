from rest_framework import serializers
from comissoes.models import RegraComissao, LancamentoComissao, PagamentoComissao, PagamentoComissaoItem


class RegraComissaoSerializer(serializers.ModelSerializer):
    empresa = serializers.IntegerField(source="regc_empr", label=RegraComissao._meta.get_field("regc_empr").verbose_name)
    filial = serializers.IntegerField(source="regc_fili", label=RegraComissao._meta.get_field("regc_fili").verbose_name)
    beneficiario = serializers.IntegerField(source="regc_bene", label=RegraComissao._meta.get_field("regc_bene").verbose_name)
    percentual = serializers.DecimalField(source="regc_perc", max_digits=5, decimal_places=2, label=RegraComissao._meta.get_field("regc_perc").verbose_name)
    ativo = serializers.BooleanField(source="regc_ativ", label=RegraComissao._meta.get_field("regc_ativ").verbose_name)
    data_inicial = serializers.DateField(source="regc_data_ini", allow_null=True, required=False, label=RegraComissao._meta.get_field("regc_data_ini").verbose_name)
    data_final = serializers.DateField(source="regc_data_fim", allow_null=True, required=False, label=RegraComissao._meta.get_field("regc_data_fim").verbose_name)
    cento_custo = serializers.IntegerField(source="regc_cecu", label=RegraComissao._meta.get_field("regc_cecu").verbose_name)
    

    class Meta:
        model = RegraComissao
        fields = [
            "regc_id",
            "empresa",
            "filial",
            "beneficiario",
            "percentual",
            "ativo",
            "data_inicial",
            "data_final",
            "cento_custo",
        ]


class LancamentoComissaoSerializer(serializers.ModelSerializer):
    empresa = serializers.IntegerField(source="lcom_empr", label=LancamentoComissao._meta.get_field("lcom_empr").verbose_name)
    filial = serializers.IntegerField(source="lcom_fili", label=LancamentoComissao._meta.get_field("lcom_fili").verbose_name)
    beneficiario = serializers.IntegerField(source="lcom_bene", label=LancamentoComissao._meta.get_field("lcom_bene").verbose_name)
    data = serializers.DateField(source="lcom_data", label=LancamentoComissao._meta.get_field("lcom_data").verbose_name)
    tipo_origem = serializers.CharField(source="lcom_tipo_origem", allow_null=True, required=False, label=LancamentoComissao._meta.get_field("lcom_tipo_origem").verbose_name)
    documento = serializers.CharField(source="lcom_docu", label=LancamentoComissao._meta.get_field("lcom_docu").verbose_name)
    base = serializers.DecimalField(source="lcom_base", max_digits=14, decimal_places=2, label=LancamentoComissao._meta.get_field("lcom_base").verbose_name)
    percentual = serializers.DecimalField(source="lcom_perc", max_digits=5, decimal_places=2, label=LancamentoComissao._meta.get_field("lcom_perc").verbose_name)
    valor = serializers.DecimalField(source="lcom_valo", max_digits=14, decimal_places=2, label=LancamentoComissao._meta.get_field("lcom_valo").verbose_name)
    status = serializers.IntegerField(source="lcom_stat", label=LancamentoComissao._meta.get_field("lcom_stat").verbose_name if hasattr(LancamentoComissao._meta.get_field("lcom_stat"), "verbose_name") else "Status")
    observacao = serializers.CharField(source="lcom_obse", allow_blank=True, allow_null=True, required=False, label=LancamentoComissao._meta.get_field("lcom_obse").verbose_name)
    cento_custo = serializers.IntegerField(source="lcom_cecu", label=LancamentoComissao._meta.get_field("lcom_cecu").verbose_name)

    class Meta:
        model = LancamentoComissao
        fields = [
            "lcom_id",
            "empresa",
            "filial",
            "lcom_regra",
            "beneficiario",
            "data",
            "tipo_origem",
            "documento",
            "base",
            "percentual",
            "valor",
            "status",
            "observacao",
            "cento_custo",
        ]


class PagamentoComissaoItemSerializer(serializers.ModelSerializer):
    valor = serializers.DecimalField(source="pgci_valo", max_digits=14, decimal_places=2, label=PagamentoComissaoItem._meta.get_field("pgci_valo").verbose_name)
    cento_custo = serializers.IntegerField(source="pgci_cecu", label=PagamentoComissaoItem._meta.get_field("pgci_cecu").verbose_name)

    class Meta:
        model = PagamentoComissaoItem
        fields = ["pgci_id", "pgci_paga", "pgci_lanc", "valor", "cento_custo"]


class PagamentoComissaoSerializer(serializers.ModelSerializer):
    empresa = serializers.IntegerField(source="pagc_empr", label=PagamentoComissao._meta.get_field("pagc_empr").verbose_name)
    filial = serializers.IntegerField(source="pagc_fili", label=PagamentoComissao._meta.get_field("pagc_fili").verbose_name)
    data = serializers.DateField(source="pagc_data", label=PagamentoComissao._meta.get_field("pagc_data").verbose_name)
    beneficiario = serializers.IntegerField(source="pagc_bene", label=PagamentoComissao._meta.get_field("pagc_bene").verbose_name)
    valor = serializers.DecimalField(source="pagc_valo", max_digits=14, decimal_places=2, label=PagamentoComissao._meta.get_field("pagc_valo").verbose_name)
    observacao = serializers.CharField(source="pagc_obse", allow_blank=True, allow_null=True, required=False, label=PagamentoComissao._meta.get_field("pagc_obse").verbose_name)
    itens = PagamentoComissaoItemSerializer(source="itens", many=True, read_only=True)
    cento_custo = serializers.IntegerField(source="pagc_cecu", label=PagamentoComissao._meta.get_field("pagc_cecu").verbose_name)
    
    class Meta:
        model = PagamentoComissao
        fields = [
            "pagc_id",
            "empresa",
            "filial",
            "data",
            "beneficiario",
            "valor",
            "observacao",
            "cento_custo",  
            "itens",
        ]
