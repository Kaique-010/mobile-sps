from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from Licencas.models import Empresas
from .models import PedidoVenda, Itenspedidovenda
from Entidades.models import Entidades
from core.serializers import BancoContextMixin
import logging

logger = logging.getLogger(__name__)


class ItemPedidoVendaSerializer(BancoContextMixin,serializers.ModelSerializer):
    class Meta:
        model = Itenspedidovenda
        exclude = ['iped_empr', 'iped_fili', 'iped_item', 'iped_pedi']

class PedidoVendaSerializer(BancoContextMixin, serializers.ModelSerializer):
    valor_total = serializers.FloatField(source='pedi_tota', read_only=True)
    cliente_nome = serializers.SerializerMethodField(read_only=True)
    empresa_nome = serializers.SerializerMethodField()
    itens = ItemPedidoVendaSerializer(many=True, write_only=True, required=True)
    pedi_empr = serializers.IntegerField(required=True)
    pedi_fili = serializers.IntegerField(required=True)
    pedi_data = serializers.DateField(required=True)
    pedi_tota = serializers.DecimalField(max_digits=15, decimal_places=2, required=True)
    pedi_forn = serializers.IntegerField(required=True) 
    pedi_nume = serializers.IntegerField(read_only=True)
    pedi_stat = serializers.IntegerField(read_only=True)

    class Meta:
        model = PedidoVenda
        fields = [
            'pedi_empr', 'pedi_fili', 'pedi_data', 'pedi_tota', 'pedi_forn',
            'itens',
            'valor_total', 'cliente_nome', 'empresa_nome','pedi_nume', 'pedi_stat'
            # outros campos que quiser
        ]

    def get_cliente_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None

        try:
            entidades = Entidades.objects.using(banco).filter(
                enti_clie=obj.pedi_forn,
                enti_empr=obj.pedi_empr,
            ).first()

            return entidades.enti_nome if entidades else None

        except Exception as e:
            logger.warning(f"Erro ao buscar cliente: {e}")
            return None

    def get_empresa_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None

        try:
            return Empresas.objects.using(banco).get(empr_codi=obj.pedi_empr).empr_nome
        except Empresas.DoesNotExist:
            logger.warning(f"Empresa com ID {obj.pedi_empr} não encontrada.")
            return None

    def create(self, validated_data):
        banco = self.context.get('banco')
        itens_data = validated_data.pop('itens', [])
        if not banco:
            raise ValidationError("Banco não definido no contexto.")
        if not itens_data:
            raise ValidationError("Itens do pedido são obrigatórios.")

        try:
            ultimo = PedidoVenda.objects.using(banco).filter(
                pedi_empr=validated_data['pedi_empr'],
                pedi_fili=validated_data['pedi_fili']
            ).order_by('-pedi_nume').first()
            validated_data['pedi_nume'] = (ultimo.pedi_nume + 1) if ultimo else 1

            pedido = PedidoVenda.objects.using(banco).create(**validated_data)

            for idx, item_data in enumerate(itens_data, start=1):
                Itenspedidovenda.objects.using(banco).create(
                    iped_empr=pedido.pedi_empr,
                    iped_fili=pedido.pedi_fili,
                    iped_item=idx,
                    iped_pedi=str(pedido.pedi_nume),
                    **item_data
                )
            return pedido

        except Exception as e:
            logger.exception("Erro inesperado ao criar pedido")
            raise ValidationError(f"Erro inesperado ao criar pedido: {str(e)}")
