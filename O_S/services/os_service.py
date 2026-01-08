from django.db import transaction, IntegrityError, InternalError, connection, connections
from django.db.models import Sum
import logging
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from ..models import Os, PecasOs, ServicosOs, OsHora
from ..utils import get_next_service_id

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
            OsService.logger.warning(f"[_to_decimal] valor inválido={value}, fallback={default}, err={e}")
            return Decimal(default)

    @staticmethod
    def _sanitize_os_data(os_data: dict):
        for k, v in os_data.items():
            if v == "":
                os_data[k] = None
        return os_data

    @staticmethod
    def _sanitize_items_list(items_data: list):
        if not items_data:
            return []
        sanitized = []
        for item in items_data:
            if isinstance(item, dict):
                sanitized_item = {k: (None if v == "" else v) for k, v in item.items()}
                sanitized.append(sanitized_item)
            else:
                sanitized.append(item)
        return sanitized

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
    def create_os(banco: str, os_data: dict, pecas_data: list, servicos_data: list, horas_data: list = None):
        if horas_data is None:
            horas_data = []
        os_data = OsService._sanitize_os_data(os_data)
        
        os_auto = os_data.get('os_auto')
        OsService.logger.info(f"[create_os] Iniciando. os_auto={os_auto}, pecas={len(pecas_data)}, servicos={len(servicos_data)}")

        with transaction.atomic(using=banco):
            os_empr = int(os_data.get('os_empr'))
            os_fili = int(os_data.get('os_fili'))
            
            # Idempotency check
            if os_auto:
                existing = Os.objects.using(banco).filter(
                    os_empr=os_empr,
                    os_fili=os_fili,
                    os_auto=os_auto
                ).first()
                if existing:
                    OsService.logger.info(f"[create_os] OS {existing.os_os} já existe (UUID={os_auto})")
                    # ... código de mapeamento igual ao anterior ...
                    existing.id_mappings = {'pecas_ids': [], 'servicos_ids': [], 'horas_ids': []}
                    return existing

            if not os_data.get('os_os'):
                os_data['os_os'] = OsService._proxima_ordem_numero(banco, os_empr, os_fili)

            if 'os_tota' not in os_data or os_data['os_tota'] is None:
                os_data['os_tota'] = Decimal('0.00')
            else:
                os_data['os_tota'] = OsService._to_decimal(os_data['os_tota'])
                
            if 'os_desc' not in os_data or os_data['os_desc'] is None:
                os_data['os_desc'] = Decimal('0.00')
            else:
                os_data['os_desc'] = OsService._to_decimal(os_data['os_desc'])

            OsService.logger.info(f"[create_os] Criando OS {os_data['os_os']} com os_tota={os_data['os_tota']}, os_desc={os_data['os_desc']}")
            
            ordem = Os.objects.using(banco).create(**os_data)
            
            OsService.logger.info(f"[create_os] OS {ordem.os_os} criada. os_tota atual={ordem.os_tota}")

            subtotal_pecas = Decimal('0.00')
            subtotal_servicos = Decimal('0.00')
            
            id_mappings = {
                'pecas_ids': [],
                'servicos_ids': [],
                'horas_ids': []
            }
            
            # ========== PEÇAS ==========
            for idx, item_data in enumerate(pecas_data, start=1):
                peca_quan = OsService._to_decimal(item_data.get('peca_quan', 0))
                peca_unit = OsService._to_decimal(item_data.get('peca_unit', 0))
                peca_desc = OsService._to_decimal(item_data.get('peca_desc', 0))

                local_id = item_data.get('peca_item')
                if local_id:
                    id_mappings['pecas_ids'].append({'local_id': local_id, 'remote_id': idx})

                peca_tota = (peca_quan * peca_unit) - peca_desc
                subtotal_pecas += peca_tota

                OsService.logger.debug(f"[create_os] Peça {idx}: {peca_quan} x {peca_unit} - {peca_desc} = {peca_tota}")

                try:
                    PecasOs.objects.using(banco).create(
                        peca_empr=ordem.os_empr,
                        peca_fili=ordem.os_fili,
                        peca_os=ordem.os_os,
                        peca_item=idx,
                        peca_prod=str(item_data.get('peca_prod') or ''),
                        peca_quan=peca_quan,
                        peca_unit=peca_unit,
                        peca_tota=peca_tota,
                        peca_desc=peca_desc,
                        peca_data=item_data.get('peca_data') or ordem.os_data_aber,
                    )
                except (IntegrityError, InternalError) as e:
                    if 'Não é permitido estoque negativo' in str(e):
                        raise ValueError(f"Estoque negativo: {item_data.get('peca_prod')}")
                    raise e

            # ========== SERVIÇOS ==========
            for idx, item_data in enumerate(servicos_data, start=1):
                serv_quan = OsService._to_decimal(item_data.get('serv_quan', 0))
                serv_unit = OsService._to_decimal(item_data.get('serv_unit', 0))
                serv_desc = OsService._to_decimal(item_data.get('serv_desc', 0))

                local_id = item_data.get('serv_item')
                serv_tota = (serv_quan * serv_unit) - serv_desc
                subtotal_servicos += serv_tota

                OsService.logger.debug(f"[create_os] Serviço: {serv_quan} x {serv_unit} - {serv_desc} = {serv_tota}")

                novo_id, _ = get_next_service_id(banco, ordem.os_os, ordem.os_empr, ordem.os_fili)
                
                if local_id:
                    id_mappings['servicos_ids'].append({'local_id': local_id, 'remote_id': novo_id})

                ServicosOs.objects.using(banco).create(
                    serv_empr=ordem.os_empr,
                    serv_fili=ordem.os_fili,
                    serv_os=ordem.os_os,
                    serv_item=novo_id,
                    serv_prod=str(item_data.get('serv_prod') or ''),
                    serv_quan=serv_quan,
                    serv_unit=serv_unit,
                    serv_tota=serv_tota,
                    serv_desc=serv_desc,
                )

            # ========== HORAS ==========
            for idx, item_data in enumerate(horas_data, start=1):
                try:
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
                    OsService.logger.error(f"[create_os] Erro hora {idx}: {e}")
                    raise e

            # ========== CALCULAR TOTAL FINAL ==========
            os_desc_global = OsService._to_decimal(ordem.os_desc, '0.00')
            os_tota_final = (subtotal_pecas + subtotal_servicos) - os_desc_global

            OsService.logger.info(
                f"[create_os] ANTES UPDATE: OS {ordem.os_os} | "
                f"Peças={subtotal_pecas} | Serviços={subtotal_servicos} | "
                f"Desc={os_desc_global} | Total Calculado={os_tota_final}"
            )

            #  raw SQL para garantir que update funcione
            with connections[banco].cursor() as cursor:
                cursor.execute(
                    f"UPDATE {Os._meta.db_table} "
                    f"SET os_tota = %s, os_desc = %s "
                    f"WHERE os_empr = %s AND os_fili = %s AND os_os = %s",
                    [os_tota_final, os_desc_global, ordem.os_empr, ordem.os_fili, ordem.os_os]
                )
                rows_updated = cursor.rowcount
                OsService.logger.info(f"[create_os] UPDATE afetou {rows_updated} linhas")

            # ✅ REFRESH da instância para pegar valores do banco
            ordem.refresh_from_db(using=banco)
            
            OsService.logger.info(
                f"[create_os] DEPOIS REFRESH: OS {ordem.os_os} | "
                f"os_tota no banco={ordem.os_tota} | os_desc={ordem.os_desc}"
            )
            
            ordem.id_mappings = id_mappings
            return ordem

    @staticmethod
    def update_os(banco: str, ordem: Os, os_updates: dict, pecas_data: list, servicos_data: list, horas_data: list = None):
        if horas_data is None:
            horas_data = []
            
        os_updates = OsService._sanitize_os_data(os_updates)
        pecas_data = OsService._sanitize_items_list(pecas_data)
        servicos_data = OsService._sanitize_items_list(servicos_data)
        horas_data = OsService._sanitize_items_list(horas_data)

        with transaction.atomic(using=banco):
            # Atualizar campos básicos
            if os_updates:
                Os.objects.using(banco).filter(
                    os_empr=ordem.os_empr,
                    os_fili=ordem.os_fili,
                    os_os=ordem.os_os
                ).update(**os_updates)
                
                for k, v in os_updates.items():
                    setattr(ordem, k, v)

            # Deletar itens antigos
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

            subtotal_pecas = Decimal('0.00')
            subtotal_servicos = Decimal('0.00')

            # Recriar peças
            for idx, item_data in enumerate(pecas_data, start=1):
                peca_quan = OsService._to_decimal(item_data.get('peca_quan', 0))
                peca_unit = OsService._to_decimal(item_data.get('peca_unit', 0))
                peca_desc = OsService._to_decimal(item_data.get('peca_desc', 0))
                peca_tota = (peca_quan * peca_unit) - peca_desc
                subtotal_pecas += peca_tota

                try:
                    PecasOs.objects.using(banco).create(
                        peca_empr=ordem.os_empr,
                        peca_fili=ordem.os_fili,
                        peca_os=ordem.os_os,
                        peca_item=idx,
                        peca_prod=str(item_data.get('peca_prod') or ''),
                        peca_quan=peca_quan,
                        peca_unit=peca_unit,
                        peca_tota=peca_tota,
                        peca_desc=peca_desc,
                        peca_data=item_data.get('peca_data') or ordem.os_data_aber,
                    )
                except (IntegrityError, InternalError) as e:
                    if 'Não é permitido estoque negativo' in str(e):
                        raise ValueError(f"Estoque negativo: {item_data.get('peca_prod')}")
                    raise e

            # Recriar serviços
            for item_data in servicos_data:
                serv_quan = OsService._to_decimal(item_data.get('serv_quan', 0))
                serv_unit = OsService._to_decimal(item_data.get('serv_unit', 0))
                serv_desc = OsService._to_decimal(item_data.get('serv_desc', 0))
                serv_tota = (serv_quan * serv_unit) - serv_desc
                subtotal_servicos += serv_tota

                novo_id, _ = get_next_service_id(banco, ordem.os_os, ordem.os_empr, ordem.os_fili)
                ServicosOs.objects.using(banco).create(
                    serv_empr=ordem.os_empr,
                    serv_fili=ordem.os_fili,
                    serv_os=ordem.os_os,
                    serv_item=novo_id,
                    serv_prod=str(item_data.get('serv_prod') or ''),
                    serv_quan=serv_quan,
                    serv_unit=serv_unit,
                    serv_tota=serv_tota,
                    serv_desc=serv_desc,
                )

            # Recriar horas
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
                    OsService.logger.error(f"[update] Erro hora {idx}: {e}")
                    raise e

            # Calcular total final
            os_desc_global = OsService._to_decimal(os_updates.get('os_desc', ordem.os_desc), '0.00')
            os_tota_final = (subtotal_pecas + subtotal_servicos) - os_desc_global

            OsService.logger.info(
                f"[update_os] Atualizando OS {ordem.os_os}: "
                f"Peças={subtotal_pecas}, Serviços={subtotal_servicos}, "
                f"Desc={os_desc_global}, Total={os_tota_final}"
            )

            with connections[banco].cursor() as cursor:
                cursor.execute(
                    f"UPDATE {Os._meta.db_table} "
                    f"SET os_tota = %s, os_desc = %s "
                    f"WHERE os_empr = %s AND os_fili = %s AND os_os = %s",
                    [os_tota_final, os_desc_global, ordem.os_empr, ordem.os_fili, ordem.os_os]
                )
            
            ordem.refresh_from_db(using=banco)
            return ordem

    @staticmethod
    def cancelar_os(banco: str, ordem: Os):
        Os.objects.using(banco).filter(
            os_empr=ordem.os_empr,
            os_fili=ordem.os_fili,
            os_os=ordem.os_os
        ).update(
            os_stat_os=3,
            os_moti_canc="Ordem Cancelada mobile"
        )
        
        ordem.os_stat_os = 3
        ordem.os_moti_canc = "Ordem Cancelada mobile"

        pecas = PecasOs.objects.using(banco).filter(
            peca_empr=ordem.os_empr,
            peca_fili=ordem.os_fili,
            peca_os=ordem.os_os
        )
        for peca in pecas:
            peca.update_estoque(quantidade=peca.peca_quan)

        servicos = ServicosOs.objects.using(banco).filter(
            serv_empr=ordem.os_empr,
            serv_fili=ordem.os_fili,
            serv_os=ordem.os_os
        )
        for servico in servicos:
            servico.update_estoque(quantidade=servico.serv_quan)

    @staticmethod
    def finalizar_os(banco: str, ordem: Os):
        Os.objects.using(banco).filter(
            os_empr=ordem.os_empr,
            os_fili=ordem.os_fili,
            os_os=ordem.os_os
        ).update(
            os_stat_os=2,
            os_data_fech=timezone.now().date()
        )
        
        ordem.os_stat_os = 2
        ordem.os_data_fech = timezone.now().date()

    @staticmethod
    def calcular_total(banco: str, ordem: Os):
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
        
        # ✅ CONSIDERAR desconto global
        os_desc = OsService._to_decimal(ordem.os_desc, '0.00')
        novo_total = (total_pecas + total_servicos) - os_desc
        
        OsService.logger.info(
            f"[calcular_total] OS {ordem.os_os}: "
            f"Peças={total_pecas}, Serviços={total_servicos}, "
            f"Desc={os_desc}, Total={novo_total}"
        )
        
        with connections[banco].cursor() as cursor:
            cursor.execute(
                f"UPDATE {Os._meta.db_table} "
                f"SET os_tota = %s "
                f"WHERE os_empr = %s AND os_fili = %s AND os_os = %s",
                [novo_total, ordem.os_empr, ordem.os_fili, ordem.os_os]
            )
            rows = cursor.rowcount
            OsService.logger.info(f"[calcular_total] UPDATE realizado. Linhas afetadas: {rows}. Novo Total={novo_total}")
        
        ordem.refresh_from_db(using=banco)
        return novo_total