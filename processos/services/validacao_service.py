# processos/services/validacao_service.py

from django.utils import timezone
from processos.models import Processo, ProcessoChecklistResposta



class ValidacaoProcessoService:

    @staticmethod
    def validar_processo(*, db_alias, empresa, filial, proc_id, usuario_id=None):
        proc = Processo.objects.using(db_alias).get(
            id=proc_id,
            proc_empr=empresa,
            proc_fili=filial,
        )

        respostas_proc = ProcessoChecklistResposta.objects.using(db_alias).filter(
            pchr_proc=proc,
            pchr_empr=empresa,
            pchr_fili=filial,
        ).select_related("pchr_item")

        erros = []

        for resposta in respostas_proc:
            item = resposta.pchr_item

            if item.chit_obrigatorio and not resposta.pchr_resp:
                erros.append(f"Item obrigatório sem resposta: {item.chit_descricao}")

            if item.chit_obrigatorio and resposta.pchr_resp == "NAO":
                erros.append(f"Item obrigatório reprovado: {item.chit_descricao}")

        if erros:
            proc.proc_status = "REPROVADO"
            proc.proc_usuario_validacao = usuario_id
            proc.proc_data_fechamento = timezone.now()
            proc.save(using=db_alias)

            return {
                "aprovado": False,
                "status": "REPROVADO",
                "erros": erros,
            }

        respostas_proc.update(
            pchr_validado=True,
            pchr_data_validacao=timezone.now(),
            pchr_usuario_validacao=usuario_id,
        )

        proc.proc_status = "APROVADO"
        proc.proc_usuario_validacao = usuario_id
        proc.proc_data_fechamento = timezone.now()
        proc.save(using=db_alias)

        return {
            "aprovado": True,
            "status": "APROVADO",
            "erros": [],
        }