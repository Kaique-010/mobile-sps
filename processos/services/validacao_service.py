from django.utils import timezone

from processos.models import Processo, ProcessoChecklistResposta


class ValidacaoProcessoService:
    @staticmethod
    def validar_processo(*, db_alias, empresa, filial, processo_id, usuario_id=None):
        processo = Processo.objects.using(db_alias).get(
            id=processo_id,
            proc_empr=empresa,
            proc_fili=filial,
        )

        respostas_proc = (
            ProcessoChecklistResposta.objects.using(db_alias)
            .filter(
                pchr_proc=processo,
                pchr_empr=empresa,
                pchr_fili=filial,
            )
            .select_related("pchr_item")
        )

        erros = []
        for resposta in respostas_proc:
            item = resposta.pchr_item
            if item.chit_obri and not resposta.pchr_resp:
                erros.append(f"Item obrigatório sem resposta: {item.chit_desc}")
            if item.chit_obri and resposta.pchr_resp == ProcessoChecklistResposta.RESP_NAO:
                erros.append(f"Item obrigatório marcado como NÃO: {item.chit_desc}")

        if erros:
            processo.proc_stat = Processo.STATUS_REPROVADO
            processo.proc_usro_vali = usuario_id
            processo.proc_data_fech = timezone.now()
            processo.save(using=db_alias)
            return {"aprovado": False, "status": Processo.STATUS_REPROVADO, "erros": erros}

        respostas_proc.update(
            pchr_vali=True,
            pchr_data_vali=timezone.now(),
            pchr_usro_vali=usuario_id,
        )
        processo.proc_stat = Processo.STATUS_APROVADO
        processo.proc_usro_vali = usuario_id
        processo.proc_data_fech = timezone.now()
        processo.save(using=db_alias)
        return {"aprovado": True, "status": Processo.STATUS_APROVADO, "erros": []}
