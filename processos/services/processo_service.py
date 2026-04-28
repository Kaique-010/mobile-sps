# processos/services/processo_service.py

from django.utils import timezone
from processos.models import Processo, ProcessoTipo
from .checklist_service import ChecklistService


class ProcessoService:

    @staticmethod
    def listar(*, db_alias, empresa, filial):
        return (
            Processo.objects.using(db_alias)
            .filter(proc_empr=empresa, proc_fili=filial)
            .select_related("proc_tipo")
            .order_by("-id")
        )

    @staticmethod
    def criar(*, db_alias, empresa, filial, tipo_id, descricao, usuario_id=None):
        tipo = ProcessoTipo.objects.using(db_alias).get(
            id=tipo_id,
            prot_empr=empresa,
            prot_fili=filial,
            prot_ativo=True,
        )

        processo = Processo.objects.using(db_alias).create(
            proc_empr=empresa,
            proc_fili=filial,
            proc_tipo=tipo,
            proc_desc=descricao,
            proc_data_aber=timezone.now(),
            proc_usro_aber=usuario_id,
            proc_usro_vali=usuario_id,
        )

        ChecklistService.gerar_respostas_para_processo(
            db_alias=db_alias,
            empresa=empresa,
            filial=filial,
            processo=processo,
        )

        return processo

    @staticmethod
    def mudar_status(*, db_alias, processo_id, empresa, filial, status):
        processo = Processo.objects.using(db_alias).get(
            id=processo_id,
            proc_empr=empresa,
            proc_fili=filial,
        )

        processo.proc_stat = status

        if status in ["APROVADO", "REPROVADO", "CANCELADO"]:
            processo.proc_data_fech = timezone.now()

        processo.save(using=db_alias)
        return processo