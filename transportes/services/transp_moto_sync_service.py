from django.db import transaction

from Entidades.models import Entidades
from transportes.models import MotoristasCadastros


class TranspMotoSyncService:
    """Sincroniza entidade de motorista com tabela dedicada de motoristas."""

    @staticmethod
    @transaction.atomic
    def sync_entidade_para_motorista(*, banco: str, empresa_id: int, filial_id: int, entidade_id: int):
        entidade = Entidades.objects.using(banco).filter(enti_empr=empresa_id, enti_clie=entidade_id).first()
        if not entidade:
            raise ValueError("Entidade não encontrada para sincronização")

        if entidade.enti_tien != 'M':
            return None

        motorista, _ = MotoristasCadastros.objects.using(banco).update_or_create(
            empresa=empresa_id,
            filial=filial_id,
            entidade=entidade.enti_clie,
            defaults={"status": "ATV" if str(entidade.enti_situ) == '1' else "INA"},
        )
        return motorista

    @staticmethod
    def sync_lote_motoristas(*, banco: str, empresa_id: int, filial_id: int):
        motoristas = Entidades.objects.using(banco).filter(enti_empr=empresa_id, enti_tien='M')
        total = 0
        for ent in motoristas.iterator():
            TranspMotoSyncService.sync_entidade_para_motorista(
                banco=banco,
                empresa_id=empresa_id,
                filial_id=filial_id,
                entidade_id=ent.enti_clie,
            )
            total += 1
        return total
