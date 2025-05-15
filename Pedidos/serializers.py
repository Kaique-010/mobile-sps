from rest_framework import serializers

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
    itens = serializers.SerializerMethodField()

    class Meta:
        model = PedidoVenda
        fields = '__all__'

    def get_itens(self, obj):
        return Itenspedidovenda.objects.filter(iped_pedi=obj.pedi_nume).values()
    
    def get_cliente_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None

        try:
            
            entidades = Entidades.objects.using(banco).filter(
                enti_clie=obj.pedi_forn, 
                enti_empr=obj.pedi_empr,
                pedi_nume=obj.pedi_nume  
            ).first()

            if entidades:
                return entidades.enti_nome
            return None

        except Exception as e:
            logger.warning(f"Erro ao buscar cliente: {e}")
            return None



    def get_empresa_nome(self, obj):
        banco = self.context.get('banco')
        print(f"[DEBUG] banco: {banco} | pedi_empr: {obj.pedi_empr}")  # 👈
        if not banco:
            return None

        try:
            return Empresas.objects.using(banco).get(empr_codi=obj.pedi_empr).empr_nome
        except Empresas.DoesNotExist:
            logger.warning(f"Empresa com ID {obj.pedi_empr} não encontrada.")
            return None


    def create(self, validated_data):
        
        banco = self.context.get('banco')
        print(f"[Pedidos de venda] banco: {banco} ")
        if not banco:
            return None
        
        itens_data = validated_data.pop('itens')
        pedido = PedidoVenda.objects.using(banco).create(**validated_data)

        for idx, item_data in enumerate(itens_data, start=1):
            Itenspedidovenda.objects.using(BancoContextMixin()).create(
                iped_empr=pedido.pedi_empr,
                iped_fili=pedido.pedi_fili,
                iped_item=idx,
                iped_pedi=pedido,
                **item_data
            )

        return pedido