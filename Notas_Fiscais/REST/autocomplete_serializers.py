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
    value = serializers.IntegerField(source="prod_codi")

    class Meta:
        model = Produtos
        fields = ["value", "label", "prod_desc", "prod_codi", "prod_refe"]

    def get_label(self, obj):
        ref = f" • REF: {obj.prod_refe}" if obj.prod_refe else ""
        return f"{obj.prod_desc}{ref}"
