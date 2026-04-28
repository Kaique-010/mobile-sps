# processos/services/checklist_service.py

from processos.models import ChecklistModelo, ProcessoChecklistResposta


class ChecklistService:

    @staticmethod
    def obter_modelo_ativo(*, db_alias, empresa, filial, proc_tipo):
        return (
            ChecklistModelo.objects.using(db_alias)
            .filter(
                chmo_empr=empresa,
                chmo_fili=filial,
                chmo_proc_tipo=proc_tipo,
                chmo_ativo=True,
            )
            .order_by("-chmo_versao")
            .first()
        )

    @staticmethod
    def gerar_respostas_para_processo(*, db_alias, empresa, filial, proc):
        modelo = ChecklistService.obter_modelo_ativo(
            db_alias=db_alias,
            empresa=empresa,
            filial=filial,
            proc_tipo=proc.proc_tipo,
        )

        if not modelo:
            return []

        respostas = []

        for item in modelo.itens.using(db_alias).all():
            resposta, _ = ProcessoChecklistResposta.objects.using(db_alias).get_or_create(
                pchr_empr=empresa,
                pchr_fili=filial,
                pchr_proc=proc,
                pchr_item=item,
            )
            respostas.append(resposta)

        return respostas

    @staticmethod
    def salvar_respostas(*, db_alias, empresa, filial, proc_id, dados, usuario_id=None):
        respostas_salvas = []

        for item_id, payload in dados.items():
            resposta = ProcessoChecklistResposta.objects.using(db_alias).get(
                pchr_empr=empresa,
                pchr_fili=filial,
                pchr_proc_id=proc_id,
                pchr_item_id=item_id,
            )

            resposta.pchr_resp = payload.get("resposta")
            resposta.pchr_obse = payload.get("observacao")
            resposta.save(using=db_alias)

            respostas_salvas.append(resposta)

        return respostas_salvas