from django.db import transaction
import logging
from decimal import Decimal, InvalidOperation
from ..models import PedidoVenda, Itenspedidovenda
from core.utils import (
    calcular_subtotal_item_bruto,
    calcular_total_item_com_desconto,
)

class PedidoVendaService:
    logger = logging.getLogger(__name__)

    @staticmethod
    def _to_decimal(value, default: str = '0.00') -> Decimal:
        """Converte valores diversos para Decimal de forma robusta.
        Trata None, string vazia e vírgula decimal. Em caso de falha, retorna default.
        """
        try:
            if value is None:
                return Decimal(default)
            if isinstance(value, Decimal):
                return value
            if isinstance(value, (int, float)):
                return Decimal(str(value))
            s = str(value).strip().replace(',', '.')
            if s == '':
                return Decimal(default)
            return Decimal(s)
        except (InvalidOperation, ValueError, TypeError) as e:
            PedidoVendaService.logger.warning("[_to_decimal] valor inválido=%r, fallback=%s, err=%s", value, default, e)
            return Decimal(default)
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
        subtotal_sum = Decimal('0.00')
        total_items_sum = Decimal('0.00')
        any_item_discount = False
        PedidoVendaService.logger.debug(
            "[PedidoService.create] Início: pedi_nume=%s pedi_desc=%s",
            getattr(pedido, 'pedi_nume', None), pedido_data.get('pedi_desc')
        )
        for idx, item_data in enumerate(itens_data, start=1):
            # cálculos
            iped_quan = PedidoVendaService._to_decimal(item_data.get('iped_quan', 0))
            iped_unit = PedidoVendaService._to_decimal(item_data.get('iped_unit', 0))
            iped_desc = PedidoVendaService._to_decimal(item_data.get('iped_desc', 0))

            subtotal_bruto = calcular_subtotal_item_bruto(iped_quan, iped_unit)
            total_item = calcular_total_item_com_desconto(iped_quan, iped_unit, iped_desc)

            subtotal_sum += Decimal(str(subtotal_bruto))
            total_items_sum += Decimal(str(total_item))
            if iped_desc and iped_desc > 0:
                any_item_discount = True

            item_data_clean = item_data.copy()
            item_data_clean.pop('iped_suto', None)
            item_data_clean.pop('iped_tota', None)

            PedidoVendaService.logger.debug(
                "[PedidoService.create] Item %d: quan=%s unit=%s desc=%s subtotal=%s total=%s",
                idx, iped_quan, iped_unit, iped_desc, subtotal_bruto, total_item
            )

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

        # Cálculo dos totais do pedido (alinhado ao serializer)
        pedido_desc_val = PedidoVendaService._to_decimal(pedido_data.get('pedi_desc', 0))
        if pedido_desc_val > 0 and any_item_discount:
            PedidoVendaService.logger.error(
                "[PedidoService.create] Conflito de descontos: desconto_total=%s e desconto_por_item presente",
                pedido_desc_val
            )
            raise ValueError("Não é possível aplicar desconto por item e desconto no total simultaneamente.")

        pedido.pedi_topr = subtotal_sum
        if any_item_discount:
            # Desconto veio dos itens
            pedido.pedi_desc = subtotal_sum - total_items_sum
            pedido.pedi_tota = total_items_sum
        else:
            # Desconto no total
            pedido.pedi_desc = pedido_desc_val
            pedido.pedi_tota = subtotal_sum - pedido_desc_val

        # Liquido (opcional): igual ao total final
        pedido.pedi_liqu = pedido.pedi_tota
        pedido.save(using=banco)

        PedidoVendaService.logger.debug(
            "[PedidoService.create] Fim: pedi_nume=%s subtotal=%s desc=%s total=%s",
            getattr(pedido, 'pedi_nume', None), pedido.pedi_topr, pedido.pedi_desc, pedido.pedi_tota
        )

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
        subtotal_sum = Decimal('0.00')
        total_items_sum = Decimal('0.00')
        any_item_discount = False
        PedidoVendaService.logger.debug(
            "[PedidoService.update] Início: pedi_nume=%s pedi_desc_update=%s",
            getattr(pedido, 'pedi_nume', None), pedido_updates.get('pedi_desc')
        )
        for idx, item_data in enumerate(itens_data, start=1):
            iped_quan = PedidoVendaService._to_decimal(item_data.get('iped_quan', 0))
            iped_unit = PedidoVendaService._to_decimal(item_data.get('iped_unit', 0))
            iped_desc = PedidoVendaService._to_decimal(item_data.get('iped_desc', 0))

            subtotal_bruto = calcular_subtotal_item_bruto(iped_quan, iped_unit)
            total_item = calcular_total_item_com_desconto(iped_quan, iped_unit, iped_desc)

            subtotal_sum += Decimal(str(subtotal_bruto))
            total_items_sum += Decimal(str(total_item))
            if iped_desc and iped_desc > 0:
                any_item_discount = True

            item_data_clean = item_data.copy()
            item_data_clean.pop('iped_suto', None)
            item_data_clean.pop('iped_tota', None)

            PedidoVendaService.logger.debug(
                "[PedidoService.update] Item %d: quan=%s unit=%s desc=%s subtotal=%s total=%s",
                idx, iped_quan, iped_unit, iped_desc, subtotal_bruto, total_item
            )

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

        # Cálculo dos totais do pedido (alinhado ao serializer)
        pedido_desc_val = PedidoVendaService._to_decimal(pedido_updates.get('pedi_desc', 0))
        if pedido_desc_val > 0 and any_item_discount:
            PedidoVendaService.logger.error(
                "[PedidoService.update] Conflito de descontos: desconto_total=%s e desconto_por_item presente",
                pedido_desc_val
            )
            raise ValueError("Não é possível aplicar desconto por item e desconto no total simultaneamente.")

        pedido.pedi_topr = subtotal_sum
        if any_item_discount:
            pedido.pedi_desc = subtotal_sum - total_items_sum
            pedido.pedi_tota = total_items_sum
        else:
            pedido.pedi_desc = pedido_desc_val
            pedido.pedi_tota = subtotal_sum - pedido_desc_val

        pedido.pedi_liqu = pedido.pedi_tota
        pedido.save(using=banco)

        PedidoVendaService.logger.debug(
            "[PedidoService.update] Fim: pedi_nume=%s subtotal=%s desc=%s total=%s",
            getattr(pedido, 'pedi_nume', None), pedido.pedi_topr, pedido.pedi_desc, pedido.pedi_tota
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