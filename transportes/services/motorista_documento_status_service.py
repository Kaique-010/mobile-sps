from dataclasses import dataclass
from datetime import date

from django.utils import timezone

from transportes.models import MotoristaDocumento


@dataclass
class PainelAlertasDocumentos:
    total: int = 0
    pendentes: int = 0
    vencendo: int = 0
    vencidos: int = 0


class MotoristaDocumentoStatusService:
    """Regra de status documental e consolidação de alertas."""

    @staticmethod
    def calcular_status(documento: MotoristaDocumento, data_base: date | None = None) -> str:
        hoje = data_base or timezone.localdate()
        if not documento.data_validade:
            return 'pendente'

        if documento.data_validade < hoje:
            return 'vencido'

        alerta_dias = documento.alerta_em_dias or 30
        dias_restantes = (documento.data_validade - hoje).days
        if dias_restantes <= alerta_dias:
            return 'vencendo'

        return 'valido'

    @classmethod
    def atualizar_status_documentos_motorista(cls, *, banco: str, empresa_id: int, entidade_id: int):
        qs = MotoristaDocumento.objects.using(banco).filter(empresa=empresa_id, entidade=entidade_id)
        atualizados = 0
        for documento in qs.iterator():
            novo_status = cls.calcular_status(documento)
            if documento.status != novo_status:
                documento.status = novo_status
                documento.save(using=banco, update_fields=['status', 'atualizado_em'])
                atualizados += 1
        return atualizados

    @classmethod
    def montar_painel_alertas(cls, *, banco: str, empresa_id: int) -> PainelAlertasDocumentos:
        qs = MotoristaDocumento.objects.using(banco).filter(empresa=empresa_id)
        painel = PainelAlertasDocumentos(total=qs.count())
        for documento in qs.iterator():
            status = cls.calcular_status(documento)
            if status == 'pendente':
                painel.pendentes += 1
            elif status == 'vencendo':
                painel.vencendo += 1
            elif status == 'vencido':
                painel.vencidos += 1
        return painel
