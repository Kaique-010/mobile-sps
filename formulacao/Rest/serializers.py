from rest_framework import serializers

from ..models import FormulaItem, FormulaProduto, FormulaSaida, OrdemProducao


class FormulaProdutoSerializer(serializers.ModelSerializer):
    produto_codigo = serializers.CharField(source="form_prod.prod_codi", read_only=True)
    produto_nome = serializers.CharField(source="form_prod.prod_nome", read_only=True)

    class Meta:
        model = FormulaProduto
        fields = [
            "form_empr",
            "form_fili",
            "produto_codigo",
            "produto_nome",
            "form_vers",
            "form_ativ",
        ]


class FormulaItemSerializer(serializers.ModelSerializer):
    insumo_codigo = serializers.CharField(source="form_insu.prod_codi", read_only=True)
    insumo_nome = serializers.CharField(source="form_insu.prod_nome", read_only=True)

    class Meta:
        model = FormulaItem
        fields = [
            "form_empr",
            "form_fili",
            "form_vers",
            "form_item",
            "insumo_codigo",
            "insumo_nome",
            "form_qtde",
            "form_perd_perc",
        ]


class FormulaSaidaSerializer(serializers.ModelSerializer):
    produto_codigo = serializers.CharField(source="said_prod.prod_codi", read_only=True)
    produto_nome = serializers.CharField(source="said_prod.prod_nome", read_only=True)

    class Meta:
        model = FormulaSaida
        fields = [
            "said_empr",
            "said_fili",
            "produto_codigo",
            "produto_nome",
            "said_quan",
            "said_perc_cust",
            "said_principal",
        ]


class OrdemProducaoSerializer(serializers.ModelSerializer):
    produto_codigo = serializers.CharField(source="op_prod.prod_codi", read_only=True)
    produto_nome = serializers.CharField(source="op_prod.prod_nome", read_only=True)

    class Meta:
        model = OrdemProducao
        fields = [
            "op_empr",
            "op_fili",
            "op_nume",
            "op_data",
            "op_data_hora",
            "produto_codigo",
            "produto_nome",
            "op_vers",
            "op_quan",
            "op_status",
            "op_lote",
        ]
