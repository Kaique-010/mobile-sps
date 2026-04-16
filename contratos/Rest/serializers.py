from rest_framework import serializers
from Entidades.models import Entidades
from Licencas.models import Empresas
from Produtos.models import Produtos
from ..models import Contratosvendas
import logging

logger = logging.getLogger(__name__)


class ContratosvendasSerializer(serializers.ModelSerializer):
    contrato_numero = serializers.IntegerField(source="cont_cont")
    empresa = serializers.IntegerField(source="cont_empr")
    filial = serializers.IntegerField(source="cont_fili")
    cliente = serializers.IntegerField(source="cont_clie")
    data_contrato = serializers.DateField(source="cont_data")
    valor_unitario = serializers.DecimalField(source="cont_unit", max_digits=15, decimal_places=6)
    quantidade = serializers.DecimalField(source="cont_quan", max_digits=15, decimal_places=3)
    total = serializers.DecimalField(source="cont_tota", max_digits=15, decimal_places=2)

    produto_nome = serializers.SerializerMethodField()
    cliente_nome = serializers.SerializerMethodField()
    empresa_nome = serializers.SerializerMethodField()

    class Meta:
        model = Contratosvendas
        fields = [
            "contrato_numero",
            "empresa",
            "filial",
            "cliente",
            "data_contrato",
            "valor_unitario",
            "quantidade",
            "total",
            "produto_nome",
            "cliente_nome",
            "empresa_nome",
        ]

    def get_produto_nome(self, obj):
        banco = self.context.get("banco")

        produto = Produtos.objects.using(banco).filter(
            prod_codi=obj.cont_prod,
            prod_empr=obj.cont_empr
        ).first()

        return produto.prod_nome if produto else None
    
    def get_cliente_nome(self, obj):
        banco = self.context.get("banco")

        cliente = Entidades.objects.using(banco).filter(
            enti_clie=obj.cont_clie,
            enti_empr=obj.cont_empr
        ).first()

        return cliente.enti_nome if cliente else None
    
    def get_empresa_nome(self, obj):
        banco = self.context.get("banco")

        empresa = Empresas.objects.using(banco).filter(
            empr_codi=obj.cont_empr
        ).first()

        return empresa.empr_nome if empresa else None