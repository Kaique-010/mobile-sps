from django.db import transaction
import logging
from decimal import Decimal, InvalidOperation
from ..models import PedidoVenda, Itenspedidovenda
from CFOP.services.services import MotorFiscal
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
        # Número do pedido precisa ser único globalmente, pois é a PK.
        ultimo = (
            PedidoVenda.objects.using(banco)
            .order_by('-pedi_nume')
            .first()
        )
        return (ultimo.pedi_nume + 1) if ultimo else 1

    @transaction.atomic
    @staticmethod
    def create_pedido_venda(banco: str, pedido_data: dict, itens_data: list, pedi_tipo_oper: str = 'VENDA'):
        pedi_empr = int(pedido_data.get('pedi_empr'))
        pedi_fili = int(pedido_data.get('pedi_fili'))

        # Define número do pedido e garante unicidade global (PK)
        numero = pedido_data.get('pedi_nume')
        if numero is None or numero == "":
            numero = PedidoVendaService._proximo_pedido_numero(banco, pedi_empr, pedi_fili)
        try:
            numero = int(numero)
        except Exception:
            numero = PedidoVendaService._proximo_pedido_numero(banco, pedi_empr, pedi_fili)
        while PedidoVenda.objects.using(banco).filter(pedi_nume=numero).exists():
            numero += 1
        pedido_data['pedi_nume'] = numero

        # Remover campo não persistente
        pedido_data.pop('tipo_oper', None)
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
            try:
                uf_origem = pedido.get_uf_origem(banco)
                uf_destino = getattr(pedido.cliente, 'enti_uf', None) or ''
                motor = MotorFiscal(uf_origem=uf_origem or '')
                pacote = motor.calcular_item(
                    pedido=pedido,
                    item=item,
                    produto=item.produto,
                    uf_destino=uf_destino or '',
                    pedi_tipo_oper=pedi_tipo_oper or 'VENDA'
                )
                base = pacote.get('base_calculo')
                aliq = pacote.get('aliquotas', {})
                vals = pacote.get('valores', {})
                if hasattr(item, 'iped_base_icms'):
                    item.iped_base_icms = base
                if hasattr(item, 'iped_pipi'):
                    item.iped_pipi = aliq.get('ipi')
                if hasattr(item, 'iped_aliq_icms'):
                    item.iped_aliq_icms = aliq.get('icms')
                if hasattr(item, 'iped_aliq_icms_st'):
                    item.iped_aliq_icms_st = aliq.get('st_aliq')
                if hasattr(item, 'iped_aliq_pis'):
                    item.iped_aliq_pis = aliq.get('pis')
                if hasattr(item, 'iped_aliq_cofi'):
                    item.iped_aliq_cofi = aliq.get('cofins')
                if hasattr(item, 'iped_vipi'):
                    item.iped_vipi = vals.get('ipi')
                if hasattr(item, 'iped_valo_icms'):
                    item.iped_valo_icms = vals.get('icms')
                if hasattr(item, 'iped_valo_icms_st'):
                    item.iped_valo_icms_st = vals.get('st')
                if hasattr(item, 'iped_valo_pis'):
                    item.iped_valo_pis = vals.get('pis')
                if hasattr(item, 'iped_valo_cofi'):
                    item.iped_valo_cofi = vals.get('cofins')
                if hasattr(item, 'iped_base_pis'):
                    item.iped_base_pis = base
                if hasattr(item, 'iped_base_cofi'):
                    item.iped_base_cofi = base
                if hasattr(item, 'iped_cst_icms') and aliq.get('icms'):
                    item.iped_cst_icms = '000'
                if hasattr(item, 'iped_cst_pis') and aliq.get('pis'):
                    item.iped_cst_pis = '01'
                if hasattr(item, 'iped_cst_cofi') and aliq.get('cofins'):
                    item.iped_cst_cofi = '01'
                item.save(using=banco)
            except Exception as e:
                PedidoVendaService.logger.exception(
                    "[PedidoService.create] erro fiscal item=%s tipo=%s uf_origem=%s uf_destino=%s err=%s",
                    idx, pedi_tipo_oper, uf_origem, uf_destino, e
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
    def update_pedido_venda(banco: str, pedido: PedidoVenda, pedido_updates: dict, itens_data: list, pedi_tipo_oper: str | None = None):
        # Atualiza campos do pedido
        pedido_updates.pop('tipo_oper', None)
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
            try:
                uf_origem = pedido.get_uf_origem(banco)
                uf_destino = getattr(pedido.cliente, 'enti_uf', None) or ''
                motor = MotorFiscal(uf_origem=uf_origem or '')
                pacote = motor.calcular_item(
                    pedido=pedido,
                    item=item,
                    produto=item.produto,
                    uf_destino=uf_destino or '',
                    pedi_tipo_oper=pedi_tipo_oper or 'VENDA'
                )
                base = pacote.get('base_calculo')
                aliq = pacote.get('aliquotas', {})
                vals = pacote.get('valores', {})
                if hasattr(item, 'iped_base_icms'):
                    item.iped_base_icms = base
                if hasattr(item, 'iped_pipi'):
                    item.iped_pipi = aliq.get('ipi')
                if hasattr(item, 'iped_aliq_icms'):
                    item.iped_aliq_icms = aliq.get('icms')
                if hasattr(item, 'iped_aliq_icms_st'):
                    item.iped_aliq_icms_st = aliq.get('st_aliq')
                if hasattr(item, 'iped_aliq_pis'):
                    item.iped_aliq_pis = aliq.get('pis')
                if hasattr(item, 'iped_aliq_cofi'):
                    item.iped_aliq_cofi = aliq.get('cofins')
                if hasattr(item, 'iped_vipi'):
                    item.iped_vipi = vals.get('ipi')
                if hasattr(item, 'iped_valo_icms'):
                    item.iped_valo_icms = vals.get('icms')
                if hasattr(item, 'iped_valo_icms_st'):
                    item.iped_valo_icms_st = vals.get('st')
                if hasattr(item, 'iped_valo_pis'):
                    item.iped_valo_pis = vals.get('pis')
                if hasattr(item, 'iped_valo_cofi'):
                    item.iped_valo_cofi = vals.get('cofins')
                if hasattr(item, 'iped_base_pis'):
                    item.iped_base_pis = base
                if hasattr(item, 'iped_base_cofi'):
                    item.iped_base_cofi = base
                if hasattr(item, 'iped_cst_icms') and aliq.get('icms'):
                    item.iped_cst_icms = '000'
                if hasattr(item, 'iped_cst_pis') and aliq.get('pis'):
                    item.iped_cst_pis = '01'
                if hasattr(item, 'iped_cst_cofi') and aliq.get('cofins'):
                    item.iped_cst_cofi = '01'
                item.save(using=banco)
            except Exception as e:
                PedidoVendaService.logger.exception(
                    "[PedidoService.update] erro fiscal item=%s tipo=%s uf_origem=%s uf_destino=%s err=%s",
                    idx, pedi_tipo_oper, uf_origem, uf_destino, e
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

class OrcamentoService:
    logger = logging.getLogger(__name__)

    @staticmethod
    def _proximo_orcamento_numero(banco: str, pedi_empr: int, pedi_fili: int) -> int:
        from Orcamentos.models import Orcamentos
        ultimo = (
            Orcamentos.objects.using(banco)
            .filter(pedi_empr=pedi_empr, pedi_fili=pedi_fili)
            .order_by('-pedi_nume')
            .first()
        )
        proximo = (ultimo.pedi_nume + 1) if ultimo else 1
        while Orcamentos.objects.using(banco).filter(pedi_nume=proximo).exists():
            proximo += 1
        return proximo

    @transaction.atomic
    @staticmethod
    def create_orcamento(banco: str, orcamento_data: dict, itens_data: list):
        from Orcamentos.models import Orcamentos, ItensOrcamento

        pedi_empr = int(orcamento_data.get('pedi_empr'))
        pedi_fili = int(orcamento_data.get('pedi_fili'))

        if not orcamento_data.get('pedi_nume'):
            orcamento_data['pedi_nume'] = OrcamentoService._proximo_orcamento_numero(
                banco, pedi_empr, pedi_fili
            )

        desconto_total = PedidoVendaService._to_decimal(orcamento_data.get('pedi_desc', 0))
        orc = Orcamentos.objects.using(banco).create(**{k: v for k, v in orcamento_data.items() if k != 'pedi_topr' and k != 'pedi_tota'})

        subtotal_sum = Decimal('0.00')
        itens_criados = []
        for idx, item in enumerate(itens_data, start=1):
            iped_quan = PedidoVendaService._to_decimal(item.get('iped_quan', 0))
            iped_unit = PedidoVendaService._to_decimal(item.get('iped_unit', 0))
            iped_desc = PedidoVendaService._to_decimal(item.get('iped_desc', 0))

            subtotal_bruto = calcular_subtotal_item_bruto(iped_quan, iped_unit)
            total_item = calcular_total_item_com_desconto(iped_quan, iped_unit, iped_desc)
            subtotal_sum += Decimal(str(subtotal_bruto))

            clean_item = item.copy()
            clean_item.pop('iped_suto', None)
            clean_item.pop('iped_tota', None)

            created = ItensOrcamento.objects.using(banco).create(
                iped_empr=orc.pedi_empr,
                iped_fili=orc.pedi_fili,
                iped_item=idx,
                iped_pedi=str(orc.pedi_nume),
                iped_data=orc.pedi_data,
                iped_forn=getattr(orc, 'pedi_forn', None),
                iped_suto=subtotal_bruto,
                iped_tota=total_item,
                **clean_item,
            )
            itens_criados.append(created)

        orc.pedi_topr = subtotal_sum
        orc.pedi_desc = desconto_total
        orc.pedi_tota = subtotal_sum - desconto_total
        if orc.pedi_tota < 0:
            orc.pedi_tota = Decimal('0.00')
        orc.save(using=banco)

        return orc

    @transaction.atomic
    @staticmethod
    def update_orcamento(banco: str, orcamento_obj, updates: dict, itens_data: list):
        from Orcamentos.models import ItensOrcamento

        updates = updates.copy()
        desconto_total = PedidoVendaService._to_decimal(updates.pop('pedi_desc', getattr(orcamento_obj, 'pedi_desc', 0)))
        for attr, value in updates.items():
            setattr(orcamento_obj, attr, value)
        orcamento_obj.save(using=banco)

        ItensOrcamento.objects.using(banco).filter(
            iped_empr=orcamento_obj.pedi_empr,
            iped_fili=orcamento_obj.pedi_fili,
            iped_pedi=str(orcamento_obj.pedi_nume),
        ).delete()

        subtotal_sum = Decimal('0.00')
        for idx, item in enumerate(itens_data, start=1):
            iped_quan = PedidoVendaService._to_decimal(item.get('iped_quan', 0))
            iped_unit = PedidoVendaService._to_decimal(item.get('iped_unit', 0))
            iped_desc = PedidoVendaService._to_decimal(item.get('iped_desc', 0))

            subtotal_bruto = calcular_subtotal_item_bruto(iped_quan, iped_unit)
            total_item = calcular_total_item_com_desconto(iped_quan, iped_unit, iped_desc)
            subtotal_sum += Decimal(str(subtotal_bruto))

            clean_item = item.copy()
            clean_item.pop('iped_suto', None)
            clean_item.pop('iped_tota', None)

            ItensOrcamento.objects.using(banco).create(
                iped_empr=orcamento_obj.pedi_empr,
                iped_fili=orcamento_obj.pedi_fili,
                iped_item=idx,
                iped_pedi=str(orcamento_obj.pedi_nume),
                iped_data=orcamento_obj.pedi_data,
                iped_forn=getattr(orcamento_obj, 'pedi_forn', None),
                iped_suto=subtotal_bruto,
                iped_tota=total_item,
                **clean_item,
            )

        orcamento_obj.pedi_topr = subtotal_sum
        orcamento_obj.pedi_desc = desconto_total
        orcamento_obj.pedi_tota = subtotal_sum - desconto_total
        if orcamento_obj.pedi_tota < 0:
            orcamento_obj.pedi_tota = Decimal('0.00')
        orcamento_obj.save(using=banco)

        return orcamento_obj
