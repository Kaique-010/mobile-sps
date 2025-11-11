from django.db import transaction
from ..models import PedidoVenda, Itenspedidovenda
from core.utils import (
    calcular_subtotal_item_bruto,
    calcular_total_item_com_desconto,
)

class PedidoVendaService:
    @staticmethod
    def _proximo_pedido_numero(banco: str, pedi_empr: int, pedi_fili: int) -> int:
        ultimo = (
            PedidoVenda.objects.using(banco)
            .filter(pedi_empr=pedi_empr, pedi_fili=pedi_fili)
            .order_by('-pedi_nume')
            .first()
        )
        return (ultimo.pedi_nume + 1) if ultimo else 1

    @transaction.atomic
    @staticmethod
    def create_pedido_venda(banco: str, pedido_data: dict, itens_data: list):
        pedi_empr = int(pedido_data.get('pedi_empr'))
        pedi_fili = int(pedido_data.get('pedi_fili'))

        # Define número do pedido se não fornecido
        if not pedido_data.get('pedi_nume'):
            pedido_data['pedi_nume'] = PedidoVendaService._proximo_pedido_numero(
                banco, pedi_empr, pedi_fili
            )

        # Cria o pedido
        pedido = PedidoVenda.objects.using(banco).create(**pedido_data)

        # Cria os itens com cálculos de subtotal e total
        itens_criados = []
        for idx, item_data in enumerate(itens_data, start=1):
            # cálculos
            subtotal_bruto = calcular_subtotal_item_bruto(
                item_data.get('iped_quan', 0), item_data.get('iped_unit', 0)
            )
            total_item = calcular_total_item_com_desconto(
                item_data.get('iped_quan', 0),
                item_data.get('iped_unit', 0),
                item_data.get('iped_desc', 0),
            )

            item_data_clean = item_data.copy()
            item_data_clean.pop('iped_suto', None)
            item_data_clean.pop('iped_tota', None)

            item = Itenspedidovenda.objects.using(banco).create(
                iped_empr=pedido.pedi_empr,
                iped_fili=pedido.pedi_fili,
                iped_item=idx,
                iped_pedi=str(pedido.pedi_nume),
                iped_data=pedido.pedi_data,
                iped_forn=pedido.pedi_forn,
                iped_vend=pedido.pedi_vend,
                iped_unli=subtotal_bruto,
                iped_suto=subtotal_bruto,
                iped_tota=total_item,
                **item_data_clean,
            )
            itens_criados.append(item)

        return pedido

    @transaction.atomic
    @staticmethod
    def update_pedido_venda(banco: str, pedido: PedidoVenda, pedido_updates: dict, itens_data: list):
        # Atualiza campos do pedido
        for attr, value in pedido_updates.items():
            setattr(pedido, attr, value)
        pedido.save(using=banco)

        # Remove itens antigos
        Itenspedidovenda.objects.using(banco).filter(
            iped_empr=pedido.pedi_empr,
            iped_fili=pedido.pedi_fili,
            iped_pedi=str(pedido.pedi_nume),
        ).delete()

        # Recria itens
        for idx, item_data in enumerate(itens_data, start=1):
            subtotal_bruto = calcular_subtotal_item_bruto(
                item_data.get('iped_quan', 0), item_data.get('iped_unit', 0)
            )
            total_item = calcular_total_item_com_desconto(
                item_data.get('iped_quan', 0),
                item_data.get('iped_unit', 0),
                item_data.get('iped_desc', 0),
            )

            item_data_clean = item_data.copy()
            item_data_clean.pop('iped_suto', None)
            item_data_clean.pop('iped_tota', None)

            Itenspedidovenda.objects.using(banco).create(
                iped_empr=pedido.pedi_empr,
                iped_fili=pedido.pedi_fili,
                iped_item=idx,
                iped_pedi=str(pedido.pedi_nume),
                iped_data=pedido.pedi_data,
                iped_forn=pedido.pedi_forn,
                iped_vend=pedido.pedi_vend,
                iped_unli=subtotal_bruto,
                iped_suto=subtotal_bruto,
                iped_tota=total_item,
                **item_data_clean,
            )

        return pedido


class proximo_pedido_numero:
    @staticmethod
    def get_proximo_numero(banco: str, pedi_empr: int = None, pedi_fili: int = None):
        qs = PedidoVenda.objects.using(banco).all()
        if pedi_empr is not None:
            qs = qs.filter(pedi_empr=pedi_empr)
        if pedi_fili is not None:
            qs = qs.filter(pedi_fili=pedi_fili)
        ultimo_pedido = qs.order_by('-pedi_nume').first()
        return (ultimo_pedido.pedi_nume + 1) if ultimo_pedido else 1