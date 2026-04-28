from core.utils import get_licenca_db_config
from processos.services.processo_service import ProcessoService
from processos.services.checklist_service import ChecklistService
from processos.services.validacao_service import ValidacaoProcessoService
from django.views.generic import View



class SalvarChecklistView(View):
    def __init__(self, *args, **kwargs):
        self.banco = get_licenca_db_config(self.request) or 'default'  
        self.empresa_id = self.request.session.get('empresa_id', 1)
        self.filial_id = self.request.session.get('filial_id', 1)
        super().__init__(*args, **kwargs)
    def post(self, request, pk):
        dados = {}

        for key, value in request.POST.items():
            if key.startswith("resposta_"):
                item_id = key.replace("resposta_", "")
                dados[item_id] = {
                    "resposta": value,
                    "observacao": request.POST.get(f"observacao_{item_id}", ""),
                }

        ChecklistService.salvar_respostas(
            db_alias=self.banco,
            empresa_id=self.empresa_id,
            filial_id=self.filial_id,
            processo_id=pk,
            dados=dados,
            usuario_id=request.session.get("usuario_id"),
        )

        messages.success(request, "Checklist salvo com sucesso.")
        return redirect("processos:detalhe", pk=pk)


class ValidarProcessoView(View):
    def __init__(self, *args, **kwargs):
        self.banco = get_licenca_db_config(self.request) or 'default'  
        self.empresa_id = self.request.session.get('empresa_id', 1)
        self.filial_id = self.request.session.get('filial_id', 1)
        super().__init__(*args, **kwargs)
    def post(self, request, pk):

        resultado = ValidacaoProcessoService.validar_processo(
            db_alias=self.banco,    
            empresa_id=self.empresa_id,
            filial_id=self.filial_id,
            processo_id=pk,
            usuario_id=request.session.get("usuario_id"),
        )

        if resultado["aprovado"]:
            messages.success(request, "Processo aprovado.")
        else:
            for erro in resultado["erros"]:
                messages.error(request, erro)

        return redirect("processos:detalhe", pk=pk)