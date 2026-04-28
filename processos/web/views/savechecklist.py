from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import View

from core.utils import get_db_from_slug
from processos.services.checklist_service import ChecklistService
from processos.services.validacao_service import ValidacaoProcessoService


class _ChecklistBaseView(View):
    def _ctx(self):
        slug = self.kwargs.get("slug")
        return {
            "slug": slug,
            "db_alias": get_db_from_slug(slug) if slug else "default",
            "empresa": self.request.session.get("empresa_id", 1),
            "filial": self.request.session.get("filial_id", 1),
            "usuario_id": self.request.session.get("usuario_id"),
        }


class SalvarChecklistView(_ChecklistBaseView):
    def post(self, request, pk, slug=None):
        cfg = self._ctx()
        dados = {}
        for key, value in request.POST.items():
            if key.startswith("resposta_"):
                item_id = key.replace("resposta_", "")
                dados[item_id] = {
                    "resposta": value,
                    "observacao": request.POST.get(f"observacao_{item_id}", ""),
                }
        ChecklistService.salvar_respostas(
            db_alias=cfg["db_alias"],
            empresa=cfg["empresa"],
            filial=cfg["filial"],
            processo_id=pk,
            dados=dados,
        )
        messages.success(request, "Checklist salvo com sucesso.")
        return redirect("processos:detalhe", slug=cfg["slug"], pk=pk)


class ValidarProcessoView(_ChecklistBaseView):
    def post(self, request, pk, slug=None):
        cfg = self._ctx()
        resultado = ValidacaoProcessoService.validar_processo(
            db_alias=cfg["db_alias"],
            empresa=cfg["empresa"],
            filial=cfg["filial"],
            processo_id=pk,
            usuario_id=cfg["usuario_id"],
        )
        if resultado["aprovado"]:
            messages.success(request, "Processo aprovado com sucesso.")
        else:
            for erro in resultado["erros"]:
                messages.error(request, erro)
        return redirect("processos:detalhe", slug=cfg["slug"], pk=pk)
