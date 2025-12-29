from django.db import transaction, IntegrityError, InternalError
from django.db.models import Sum
import logging
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from ..models import Os, PecasOs, ServicosOs, OsHora
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

    @staticmethod
    def _sanitize_os_data(os_data: dict):
        for k, v in os_data.items():
            if v == "":
                os_data[k] = None
        return os_data

    @staticmethod
    def create_os(banco: str, os_data: dict, pecas_data: list, servicos_data: list, horas_data: list = None):
        if horas_data is None:
            horas_data = []
        os_data = OsService._sanitize_os_data(os_data)
        
        os_auto = os_data.get('os_auto')
        OsService.logger.info(f"[OsService.create_os] Iniciando criação. os_auto={os_auto}, pecas={len(pecas_data)}, servicos={len(servicos_data)}")

        with transaction.atomic(using=banco):
            os_empr = int(os_data.get('os_empr'))
            os_fili = int(os_data.get('os_fili'))
            
            # Idempotency check inside transaction
            os_auto = os_data.get('os_auto')
            if os_auto:
                existing = Os.objects.using(banco).filter(
                    os_empr=os_empr,
                    os_fili=os_fili,
                    os_auto=os_auto
                ).first()
                if existing:
                    OsService.logger.info(f"OS {existing.os_os} já existe (UUID={os_auto}). Retornando existente.")
                    
                    # Reconstruir mapeamentos para o cliente
                    id_mappings = {
                        'pecas_ids': [],
                        'servicos_ids': [],
                        'horas_ids': []
                    }
                    
                    try:
                        # Peças
                        existing_pecas = PecasOs.objects.using(banco).filter(
                            peca_empr=existing.os_empr,
                            peca_fili=existing.os_fili,
                            peca_os=existing.os_os
                        ).order_by('peca_item')
                        
                        for idx, item_data in enumerate(pecas_data):
                            if idx < len(existing_pecas):
                                local_id = item_data.get('peca_item')
                                if local_id:
                                    id_mappings['pecas_ids'].append({
                                        'local_id': local_id, 
                                        'remote_id': existing_pecas[idx].peca_item
                                    })
                        
                        # Serviços
                        existing_servicos = ServicosOs.objects.using(banco).filter(
                            serv_empr=existing.os_empr,
                            serv_fili=existing.os_fili,
                            serv_os=existing.os_os
                        ).order_by('serv_item')
                        
                        for idx, item_data in enumerate(servicos_data):
                            if idx < len(existing_servicos):
                                local_id = item_data.get('serv_item')
                                if local_id:
                                    id_mappings['servicos_ids'].append({
                                        'local_id': local_id, 
                                        'remote_id': existing_servicos[idx].serv_item
                                    })
                                    
                        # Horas
                        existing_horas = OsHora.objects.using(banco).filter(
                            os_hora_empr=existing.os_empr,
                            os_hora_fili=existing.os_fili,
                            os_hora_os=existing.os_os
                        ).order_by('os_hora_item')
                        
                        for idx, item_data in enumerate(horas_data):
                            if idx < len(existing_horas):
                                local_id = item_data.get('os_hora_item')
                                if local_id:
                                    id_mappings['horas_ids'].append({
                                        'local_id': local_id, 
                                        'remote_id': existing_horas[idx].os_hora_item
                                    })
                                    
                    except Exception as e:
                        OsService.logger.error(f"Erro ao reconstruir mapeamentos na OS existente {existing.os_os}: {e}")

                    existing.id_mappings = id_mappings
                    return existing

            if not os_data.get('os_os'):
                os_data['os_os'] = OsService._proxima_ordem_numero(banco, os_empr, os_fili)

            ordem = Os.objects.using(banco).create(**os_data)

            subtotal_sum = Decimal('0.00')
            total_items_sum = Decimal('0.00')
            
            id_mappings = {
                'pecas_ids': [],
                'servicos_ids': [],
                'horas_ids': []
            }
            
            # Peças
            for idx, item_data in enumerate(pecas_data, start=1):
                peca_quan = OsService._to_decimal(item_data.get('peca_quan', 0))
                peca_unit = OsService._to_decimal(item_data.get('peca_unit', 0))
                peca_desc = Decimal('0.00')


                # Capture local ID (UUID) for mapping
                local_id = item_data.get('peca_item')
                if local_id:
                     id_mappings['pecas_ids'].append({'local_id': local_id, 'remote_id': idx})

                subtotal_bruto = calcular_subtotal_item_bruto(peca_quan, peca_unit)
                total_item = calcular_total_item_com_desconto(peca_quan, peca_unit, peca_desc)

                subtotal_sum += Decimal(str(subtotal_bruto))
                total_items_sum += Decimal(str(total_item))

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
            for idx, item_data in enumerate(servicos_data, start=1):
                serv_quan = OsService._to_decimal(item_data.get('serv_quan', 0))
                serv_unit = OsService._to_decimal(item_data.get('serv_unit', 0))
                # serv_desc = OsService._to_decimal(item_data.get('serv_desc', 0))
                # Remover descontos conforme solicitado
                serv_desc = Decimal('0.00')

                # Capture local ID (UUID) for mapping
                local_id = item_data.get('serv_item')
                
                subtotal_bruto = calcular_subtotal_item_bruto(serv_quan, serv_unit)
                total_item = calcular_total_item_com_desconto(serv_quan, serv_unit, serv_desc)

                subtotal_sum += Decimal(str(subtotal_bruto))
                total_items_sum += Decimal(str(total_item))

                novo_id, _ = get_next_service_id(banco, ordem.os_os, ordem.os_empr, ordem.os_fili)
                
                if local_id:
                     id_mappings['servicos_ids'].append({'local_id': local_id, 'remote_id': novo_id})

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

            # Horas
            for idx, item_data in enumerate(horas_data, start=1):
                try:
                    # Capture local ID (UUID) for mapping
                    local_id = item_data.get('os_hora_item')
                    if local_id:
                         id_mappings['horas_ids'].append({'local_id': local_id, 'remote_id': idx})

                    OsHora.objects.using(banco).create(
                        os_hora_empr=ordem.os_empr,
                        os_hora_fili=ordem.os_fili,
                        os_hora_os=ordem.os_os,
                        os_hora_item=idx,
                        os_hora_data=item_data.get('os_hora_data') or ordem.os_data_aber,
                        os_hora_manh_ini=item_data.get('os_hora_manh_ini'),
                        os_hora_manh_fim=item_data.get('os_hora_manh_fim'),
                        os_hora_tard_ini=item_data.get('os_hora_tard_ini'),
                        os_hora_tard_fim=item_data.get('os_hora_tard_fim'),
                        os_hora_tota=OsService._to_decimal(item_data.get('os_hora_tota', 0)),
                        os_hora_km_sai=item_data.get('os_hora_km_sai'),
                        os_hora_km_che=item_data.get('os_hora_km_che'),
                        os_hora_oper=item_data.get('os_hora_oper'),
                        os_hora_equi=item_data.get('os_hora_equi'),
                        os_hora_obse=item_data.get('os_hora_obse'),
                    )
                except Exception as e:
                    OsService.logger.error(f"[OsService.create] Erro ao criar hora item {idx}: {e}")
                    raise e

            Os.objects.using(banco).filter(
                os_empr=ordem.os_empr,
                os_fili=ordem.os_fili,
                os_os=ordem.os_os
            ).update(
                os_desc=ordem.os_desc,
                os_tota=ordem.os_tota,

            )
            ordem.id_mappings = id_mappings
            return ordem

    @staticmethod
    def update_os(banco: str, ordem: Os, os_updates: dict, pecas_data: list, servicos_data: list, horas_data: list = None):
        if horas_data is None:
            horas_data = []
            
        # Sanitize updates
        os_updates = OsService._sanitize_os_data(os_updates)
        pecas_data = OsService._sanitize_items_list(pecas_data)
        servicos_data = OsService._sanitize_items_list(servicos_data)
        horas_data = OsService._sanitize_items_list(horas_data)

        with transaction.atomic(using=banco):
            # Update basic fields using filter/update
            if os_updates:
                Os.objects.using(banco).filter(
                    os_empr=ordem.os_empr,
                    os_fili=ordem.os_fili,
                    os_os=ordem.os_os
                ).update(**os_updates)
                
                # Update local instance
                for k, v in os_updates.items():
                    setattr(ordem, k, v)

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
            OsHora.objects.using(banco).filter(
                os_hora_empr=ordem.os_empr,
                os_hora_fili=ordem.os_fili,
                os_hora_os=ordem.os_os,
            ).delete()

            subtotal_sum = Decimal('0.00')
            total_items_sum = Decimal('0.00')
            any_item_discount = False

            for idx, item_data in enumerate(pecas_data, start=1):
                peca_quan = OsService._to_decimal(item_data.get('peca_quan', 0))
                peca_unit = OsService._to_decimal(item_data.get('peca_unit', 0))
                # peca_desc = OsService._to_decimal(item_data.get('peca_desc', 0))
                # Remover descontos conforme solicitado
                peca_desc = Decimal('0.00')

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

            # Horas
            for idx, item_data in enumerate(horas_data, start=1):
                try:
                    OsHora.objects.using(banco).create(
                        os_hora_empr=ordem.os_empr,
                        os_hora_fili=ordem.os_fili,
                        os_hora_os=ordem.os_os,
                        os_hora_item=idx,
                        os_hora_data=item_data.get('os_hora_data') or ordem.os_data_aber,
                        os_hora_manh_ini=item_data.get('os_hora_manh_ini'),
                        os_hora_manh_fim=item_data.get('os_hora_manh_fim'),
                        os_hora_tard_ini=item_data.get('os_hora_tard_ini'),
                        os_hora_tard_fim=item_data.get('os_hora_tard_fim'),
                        os_hora_tota=OsService._to_decimal(item_data.get('os_hora_tota', 0)),
                        os_hora_km_sai=item_data.get('os_hora_km_sai'),
                        os_hora_km_che=item_data.get('os_hora_km_che'),
                        os_hora_oper=item_data.get('os_hora_oper'),
                        os_hora_equi=item_data.get('os_hora_equi'),
                        os_hora_obse=item_data.get('os_hora_obse'),
                    )
                except Exception as e:
                    OsService.logger.error(f"[OsService.update] Erro ao criar hora item {idx}: {e}")
                    raise e

            os_desc_val = OsService._to_decimal(os_updates.get('os_desc', 0))
            if os_desc_val > 0 and any_item_discount:
                OsService.logger.error(
                    "[OsService.update] Conflito de descontos: desconto_total=%s e desconto_por_item presente",
                    os_desc_val
                )
                raise ValueError("Não é possível aplicar desconto por item e desconto no total simultaneamente.")

            
            if any_item_discount:
                ordem.os_desc = subtotal_sum - total_items_sum
                ordem.os_tota = total_items_sum
            else:
                ordem.os_desc = os_desc_val
                ordem.os_tota = subtotal_sum - os_desc_val

            # Update using filter/update to avoid composite PK issues
            Os.objects.using(banco).filter(
                os_empr=ordem.os_empr,
                os_fili=ordem.os_fili,
                os_os=ordem.os_os
            ).update(
                os_desc=ordem.os_desc,
                os_tota=ordem.os_tota,

            )

            OsService.logger.debug(
                "[OsService.update] Fim: os_os=%s subtotal=%s desc=%s total=%s",
                getattr(ordem, 'os_os', None), ordem.os_desc, ordem.os_tota
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

    @staticmethod
    def calcular_total(banco: str, ordem: Os):
        """
        Calcula o total da OS somando peças e serviços e atualiza no banco.
        """
        total_pecas = PecasOs.objects.using(banco).filter(
            peca_empr=ordem.os_empr,
            peca_fili=ordem.os_fili,
            peca_os=ordem.os_os
        ).aggregate(total=Sum('peca_tota'))['total'] or Decimal('0.00')
        
        total_servicos = ServicosOs.objects.using(banco).filter(
            serv_empr=ordem.os_empr,
            serv_fili=ordem.os_fili,
            serv_os=ordem.os_os
        ).aggregate(total=Sum('serv_tota'))['total'] or Decimal('0.00')
        
        novo_total = total_pecas + total_servicos
        
        # Update using filter/update to avoid composite PK issues
        Os.objects.using(banco).filter(
            os_empr=ordem.os_empr,
            os_fili=ordem.os_fili,
            os_os=ordem.os_os
        ).update(
            os_tota=novo_total
        )
        
        # Update local instance
        ordem.os_tota = novo_total
        return novo_total