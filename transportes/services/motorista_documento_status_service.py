from dataclasses import dataclass
from datetime import date

from django.conf import settings
from django.utils import timezone

from transportes.models import MotoristaDadosComplementares, MotoristaDocumento


@dataclass
class PainelAlertasDocumentos:
    total: int = 0
    pendentes: int = 0
    vencendo: int = 0
    vencidos: int = 0
    cnh_vencendo: int = 0
    cnh_vencidos: int = 0
    ear_vencendo: int = 0
    ear_vencidos: int = 0


@dataclass
class AlertaDocumentoItem:
    entidade_id: int
    origem: str
    descricao: str
    data_validade: date | None
    dias_restantes: int | None
    status: str


class MotoristaDocumentoStatusService:
    """Regra de status documental e consolidação de alertas."""

    @staticmethod
    def calcular_status_por_validade(
        data_validade: date | None,
        *,
        alerta_dias: int = 30,
        data_base: date | None = None,
    ) -> tuple[str, int | None]:
        if data_base is not None:
            hoje = data_base
        else:
            try:
                if getattr(settings, "USE_TZ", False):
                    hoje = timezone.localdate()
                else:
                    hoje = date.today()
            except Exception:
                hoje = date.today()
        if not data_validade:
            return 'pendente', None

        if data_validade < hoje:
            return 'vencido', (data_validade - hoje).days

        dias_restantes = (data_validade - hoje).days
        if dias_restantes <= alerta_dias:
            return 'vencendo', dias_restantes

        return 'valido', dias_restantes

    @classmethod
    def calcular_status(cls, documento: MotoristaDocumento, data_base: date | None = None) -> str:
        alerta_dias = documento.alerta_em_dias or 30
        status, _dias_restantes = cls.calcular_status_por_validade(
            documento.data_validade,
            alerta_dias=alerta_dias,
            data_base=data_base,
        )
        return status

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
        total_docs = qs.count()
        painel = PainelAlertasDocumentos(total=total_docs)
        for documento in qs.iterator():
            status = cls.calcular_status(documento)
            if status == 'pendente':
                painel.pendentes += 1
            elif status == 'vencendo':
                painel.vencendo += 1
            elif status == 'vencido':
                painel.vencidos += 1

        dados_qs = MotoristaDadosComplementares.objects.using(banco).filter(empresa=empresa_id)
        for dados in dados_qs.iterator():
            if dados.cnh_validade:
                status, _dias = cls.calcular_status_por_validade(dados.cnh_validade, alerta_dias=30)
                if status == 'vencendo':
                    painel.vencendo += 1
                    painel.cnh_vencendo += 1
                elif status == 'vencido':
                    painel.vencidos += 1
                    painel.cnh_vencidos += 1

            if dados.ear_validade:
                status, _dias = cls.calcular_status_por_validade(dados.ear_validade, alerta_dias=30)
                if status == 'vencendo':
                    painel.vencendo += 1
                    painel.ear_vencendo += 1
                elif status == 'vencido':
                    painel.vencidos += 1
                    painel.ear_vencidos += 1

        painel.total = total_docs + (painel.cnh_vencendo + painel.cnh_vencidos) + (painel.ear_vencendo + painel.ear_vencidos)
        return painel

    @classmethod
    def listar_itens_alerta(
        cls,
        *,
        banco: str,
        empresa_id: int,
        status: str | None = None,
        entidade_id: int | None = None,
        filial_id: int | None = None,
    ) -> list[AlertaDocumentoItem]:
        itens: list[AlertaDocumentoItem] = []

        docs_qs = MotoristaDocumento.objects.using(banco).filter(empresa=empresa_id)
        if entidade_id is not None:
            docs_qs = docs_qs.filter(entidade=entidade_id)
        if filial_id is not None:
            docs_qs = docs_qs.filter(filial=filial_id)

        for doc in docs_qs.iterator():
            doc_status = cls.calcular_status(doc)
            if status and doc_status != status:
                continue
            if doc_status not in {'vencendo', 'vencido'}:
                continue
            _status, dias_restantes = cls.calcular_status_por_validade(
                doc.data_validade,
                alerta_dias=(doc.alerta_em_dias or 30),
            )
            itens.append(
                AlertaDocumentoItem(
                    entidade_id=doc.entidade,
                    origem='documento',
                    descricao=doc.tipo_doc,
                    data_validade=doc.data_validade,
                    dias_restantes=dias_restantes,
                    status=doc_status,
                )
            )

        dados_qs = MotoristaDadosComplementares.objects.using(banco).filter(empresa=empresa_id)
        if entidade_id is not None:
            dados_qs = dados_qs.filter(entidade=entidade_id)
        if filial_id is not None:
            dados_qs = dados_qs.filter(filial=filial_id)

        for dados in dados_qs.iterator():
            if dados.cnh_validade:
                cnh_status, cnh_dias = cls.calcular_status_por_validade(dados.cnh_validade, alerta_dias=30)
                if cnh_status in {'vencendo', 'vencido'} and (not status or cnh_status == status):
                    itens.append(
                        AlertaDocumentoItem(
                            entidade_id=dados.entidade,
                            origem='cadastro',
                            descricao='CNH',
                            data_validade=dados.cnh_validade,
                            dias_restantes=cnh_dias,
                            status=cnh_status,
                        )
                    )

            if dados.ear_validade:
                ear_status, ear_dias = cls.calcular_status_por_validade(dados.ear_validade, alerta_dias=30)
                if ear_status in {'vencendo', 'vencido'} and (not status or ear_status == status):
                    itens.append(
                        AlertaDocumentoItem(
                            entidade_id=dados.entidade,
                            origem='cadastro',
                            descricao='EAR',
                            data_validade=dados.ear_validade,
                            dias_restantes=ear_dias,
                            status=ear_status,
                        )
                    )

        itens.sort(
            key=lambda i: (
                0 if i.status == 'vencido' else 1,
                i.data_validade or date.max,
                i.entidade_id,
                i.descricao,
            )
        )
        return itens

    @classmethod
    def entidades_com_alerta(
        cls,
        *,
        banco: str,
        empresa_id: int,
        status: str,
    ) -> set[int]:
        itens = cls.listar_itens_alerta(banco=banco, empresa_id=empresa_id, status=status)
        return {i.entidade_id for i in itens}
