# notas_fiscais/api/autocomplete_serializers.py

from rest_framework import serializers
from Entidades.models import Entidades
from Produtos.models import Produtos


class EntidadeAutocompleteSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()

    class Meta:
        model = Entidades
        fields = ["value", "label", "enti_clie", "enti_nome", "enti_cnpj", "enti_cpf"]

    def get_label(self, obj):
        doc = obj.enti_cnpj or obj.enti_cpf or ""
        return f"{obj.enti_nome} • {doc}"

    def get_value(self, obj):
        return obj.enti_clie


class ProdutoAutocompleteSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    value = serializers.CharField(source="prod_codi")
    prod_desc = serializers.CharField(source="prod_nome")

    class Meta:
        model = Produtos
        fields = ["value", "label", "prod_desc", "prod_codi", "prod_coba"]

    def get_label(self, obj):
        ref = getattr(obj, "prod_coba", None)
        if ref:
            return f"{obj.prod_nome} • COD: {obj.prod_codi} • REF: {ref}"
        return f"{obj.prod_nome} • COD: {obj.prod_codi}"

    
