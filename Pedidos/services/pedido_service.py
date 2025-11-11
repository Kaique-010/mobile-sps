from re import S
from django.db import transaction
from ..models import PedidoVenda, Itenspedidovenda

class PedidoVendaService:
    @transaction.atomic
    @staticmethod
    def create_pedido_venda(pedido_venda_data, itens_pedido_data):
        # Cria o pedido de venda
        pedido_venda = PedidoVenda.objects.create(**pedido_venda_data)
        
        # Cria os itens do pedido
        for item_data in itens_pedido_data:
            Itenspedidovenda.objects.create(iped_pedi=pedido_venda, **item_data)
        
        return pedido_venda
