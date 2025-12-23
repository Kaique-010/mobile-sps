from django.db import transaction, IntegrityError, InternalError
import logging
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from ..models import Os, PecasOs, ServicosOs
from ..utils import get_next_service_id
from core.utils import (
    calcular_subtotal_item_bruto,
    calcular_total_item_com_desconto,
)


class OsService:
    logger = logging.getLogger(__name__)

    @staticmethod
    def _to_decimal(value, default: str = '0.00') -> Decimal:
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
            OsService.logger.warning("[_to_decimal] valor inválido=%r, fallback=%s, err=%s", value, default, e)
            return Decimal(default)

    @staticmethod
    def _proxima_ordem_numero(banco: str, os_empr: int, os_fili: int) -> int:
        ultimo = (
            Os.objects.using(banco)
            .filter(os_empr=os_empr, os_fili=os_fili)
            .order_by('-os_os')
            .first()
        )
        return (ultimo.os_os + 1) if ultimo else 1

    @transaction.atomic
    @staticmethod
    def create_os(banco: str, os_data: dict, pecas_data: list, servicos_data: list):
        os_empr = int(os_data.get('os_empr'))
        os_fili = int(os_data.get('os_fili'))

        if not os_data.get('os_os'):
            os_data['os_os'] = OsService._proxima_ordem_numero(banco, os_empr, os_fili)

        ordem = Os.objects.using(banco).create(**os_data)

        subtotal_sum = Decimal('0.00')
        total_items_sum = Decimal('0.00')
        any_item_discount = False

        # Peças
        for idx, item_data in enumerate(pecas_data, start=1):
            peca_quan = OsService._to_decimal(item_data.get('peca_quan', 0))
            peca_unit = OsService._to_decimal(item_data.get('peca_unit', 0))
            peca_desc = OsService._to_decimal(item_data.get('peca_desc', 0))

            subtotal_bruto = calcular_subtotal_item_bruto(peca_quan, peca_unit)
            total_item = calcular_total_item_com_desconto(peca_quan, peca_unit, peca_desc)

            subtotal_sum += Decimal(str(subtotal_bruto))
            total_items_sum += Decimal(str(total_item))
            if peca_desc and peca_desc > 0:
                any_item_discount = True

            try:
                item = PecasOs.objects.using(banco).create(
                    peca_empr=ordem.os_empr,
                    peca_fili=ordem.os_fili,
                    peca_os=ordem.os_os,
                    peca_item=idx,
                    peca_prod=str(item_data.get('peca_prod') or ''),
                    peca_quan=peca_quan,
                    peca_unit=peca_unit,
                    peca_tota=total_item,
                    peca_desc=peca_desc,
                    peca_data=item_data.get('peca_data') or ordem.os_data_aber,
                )
            except (IntegrityError, InternalError) as e:
                if 'Não é permitido estoque negativo' in str(e):
                    raise ValueError(f"Não é permitido estoque negativo para o produto {item_data.get('peca_prod')}.")
                raise e
            OsService.logger.debug(
                "[OsService.create] Peça %d: prod=%s quan=%s unit=%s desc=%s subtotal=%s total=%s",
                idx, item.peca_prod, peca_quan, peca_unit, peca_desc, subtotal_bruto, total_item
            )

        # Serviços
        for item_data in servicos_data:
            serv_quan = OsService._to_decimal(item_data.get('serv_quan', 0))
            serv_unit = OsService._to_decimal(item_data.get('serv_unit', 0))
            serv_desc = OsService._to_decimal(item_data.get('serv_desc', 0))

            subtotal_bruto = calcular_subtotal_item_bruto(serv_quan, serv_unit)
            total_item = calcular_total_item_com_desconto(serv_quan, serv_unit, serv_desc)

            subtotal_sum += Decimal(str(subtotal_bruto))
            total_items_sum += Decimal(str(total_item))
            if serv_desc and serv_desc > 0:
                any_item_discount = True

            novo_id, _ = get_next_service_id(banco, ordem.os_os, ordem.os_empr, ordem.os_fili)
            item = ServicosOs.objects.using(banco).create(
                serv_empr=ordem.os_empr,
                serv_fili=ordem.os_fili,
                serv_os=ordem.os_os,
                serv_item=novo_id,
                serv_prod=str(item_data.get('serv_prod') or ''),
                serv_quan=serv_quan,
                serv_unit=serv_unit,
                serv_tota=total_item,
                serv_desc=serv_desc,
            )
            OsService.logger.debug(
                "[OsService.create] Serviço %s: prod=%s quan=%s unit=%s desc=%s subtotal=%s total=%s",
                item.serv_item, item.serv_prod, serv_quan, serv_unit, serv_desc, subtotal_bruto, total_item
            )

        os_desc_val = OsService._to_decimal(os_data.get('os_desc', 0))
        if os_desc_val > 0 and any_item_discount:
            OsService.logger.error(
                "[OsService.create] Conflito de descontos: desconto_total=%s e desconto_por_item presente",
                os_desc_val
            )
            raise ValueError("Não é possível aplicar desconto por item e desconto no total simultaneamente.")

        os_topr = subtotal_sum
        if any_item_discount:
            ordem.os_desc = subtotal_sum - total_items_sum
            ordem.os_tota = total_items_sum
        else:
            ordem.os_desc = os_desc_val
            ordem.os_tota = subtotal_sum - os_desc_val

        ordem.save(using=banco)
        OsService.logger.debug(
            "[OsService.create] Fim: os_os=%s subtotal=%s desc=%s total=%s",
            getattr(ordem, 'os_os', None), os_topr, ordem.os_desc, ordem.os_tota
        )
        return ordem

    @transaction.atomic
    @staticmethod
    def update_os(banco: str, ordem: Os, os_updates: dict, pecas_data: list, servicos_data: list):
        for attr, value in os_updates.items():
            setattr(ordem, attr, value)
        ordem.save(using=banco)

        PecasOs.objects.using(banco).filter(
            peca_empr=ordem.os_empr,
            peca_fili=ordem.os_fili,
            peca_os=ordem.os_os,
        ).delete()
        ServicosOs.objects.using(banco).filter(
            serv_empr=ordem.os_empr,
            serv_fili=ordem.os_fili,
            serv_os=ordem.os_os,
        ).delete()

        subtotal_sum = Decimal('0.00')
        total_items_sum = Decimal('0.00')
        any_item_discount = False

        for idx, item_data in enumerate(pecas_data, start=1):
            peca_quan = OsService._to_decimal(item_data.get('peca_quan', 0))
            peca_unit = OsService._to_decimal(item_data.get('peca_unit', 0))
            peca_desc = OsService._to_decimal(item_data.get('peca_desc', 0))

            subtotal_bruto = calcular_subtotal_item_bruto(peca_quan, peca_unit)
            total_item = calcular_total_item_com_desconto(peca_quan, peca_unit, peca_desc)

            subtotal_sum += Decimal(str(subtotal_bruto))
            total_items_sum += Decimal(str(total_item))
            if peca_desc and peca_desc > 0:
                any_item_discount = True

            try:
                PecasOs.objects.using(banco).create(
                    peca_empr=ordem.os_empr,
                    peca_fili=ordem.os_fili,
                    peca_os=ordem.os_os,
                    peca_item=idx,
                    peca_prod=str(item_data.get('peca_prod') or ''),
                    peca_quan=peca_quan,
                    peca_unit=peca_unit,
                    peca_tota=total_item,
                    peca_desc=peca_desc,
                    peca_data=item_data.get('peca_data') or ordem.os_data_aber,
                )
            except (IntegrityError, InternalError) as e:
                if 'Não é permitido estoque negativo' in str(e):
                    raise ValueError(f"Não é permitido estoque negativo para o produto {item_data.get('peca_prod')}.")
                raise e

        for item_data in servicos_data:
            serv_quan = OsService._to_decimal(item_data.get('serv_quan', 0))
            serv_unit = OsService._to_decimal(item_data.get('serv_unit', 0))
            serv_desc = OsService._to_decimal(item_data.get('serv_desc', 0))

            subtotal_bruto = calcular_subtotal_item_bruto(serv_quan, serv_unit)
            total_item = calcular_total_item_com_desconto(serv_quan, serv_unit, serv_desc)

            subtotal_sum += Decimal(str(subtotal_bruto))
            total_items_sum += Decimal(str(total_item))
            if serv_desc and serv_desc > 0:
                any_item_discount = True

            novo_id, _ = get_next_service_id(banco, ordem.os_os, ordem.os_empr, ordem.os_fili)
            ServicosOs.objects.using(banco).create(
                serv_empr=ordem.os_empr,
                serv_fili=ordem.os_fili,
                serv_os=ordem.os_os,
                serv_item=novo_id,
                serv_prod=str(item_data.get('serv_prod') or ''),
                serv_quan=serv_quan,
                serv_unit=serv_unit,
                serv_tota=total_item,
                serv_desc=serv_desc,
            )

        os_desc_val = OsService._to_decimal(os_updates.get('os_desc', 0))
        if os_desc_val > 0 and any_item_discount:
            OsService.logger.error(
                "[OsService.update] Conflito de descontos: desconto_total=%s e desconto_por_item presente",
                os_desc_val
            )
            raise ValueError("Não é possível aplicar desconto por item e desconto no total simultaneamente.")

        os_topr = subtotal_sum
        if any_item_discount:
            ordem.os_desc = subtotal_sum - total_items_sum
            ordem.os_tota = total_items_sum
        else:
            ordem.os_desc = os_desc_val
            ordem.os_tota = subtotal_sum - os_desc_val

        ordem.save(using=banco)
        OsService.logger.debug(
            "[OsService.update] Fim: os_os=%s subtotal=%s desc=%s total=%s",
            getattr(ordem, 'os_os', None), os_topr, ordem.os_desc, ordem.os_tota
        )
        return ordem

    @staticmethod
    def cancelar_os(banco: str, ordem: Os):
        """
        Cancela a OS e devolve os itens para o estoque.
        """
        # Update using filter/update to avoid composite PK issues in Django
        Os.objects.using(banco).filter(
            os_empr=ordem.os_empr,
            os_fili=ordem.os_fili,
            os_os=ordem.os_os
        ).update(
            os_stat_os=3,
            os_moti_canc="Ordem Cancelada mobile"
        )
        
        # Update local instance
        ordem.os_stat_os = 3
        ordem.os_moti_canc = "Ordem Cancelada mobile"

        # Return parts to stock
        pecas = PecasOs.objects.using(banco).filter(
            peca_empr=ordem.os_empr,
            peca_fili=ordem.os_fili,
            peca_os=ordem.os_os
        )
        for peca in pecas:
            peca.update_estoque(quantidade=peca.peca_quan)

        # Return services to stock
        servicos = ServicosOs.objects.using(banco).filter(
            serv_empr=ordem.os_empr,
            serv_fili=ordem.os_fili,
            serv_os=ordem.os_os
        )
        for servico in servicos:
            servico.update_estoque(quantidade=servico.serv_quan)

    @staticmethod
    def finalizar_os(banco: str, ordem: Os):
        """
        Finaliza a OS atualizando status e data de fechamento.
        """
        Os.objects.using(banco).filter(
            os_empr=ordem.os_empr,
            os_fili=ordem.os_fili,
            os_os=ordem.os_os
        ).update(
            os_stat_os=2,
            os_data_fech=timezone.now().date()
        )
        
        # Update local instance
        ordem.os_stat_os = 2
        ordem.os_data_fech = timezone.now().date()