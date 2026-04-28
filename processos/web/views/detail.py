from django.views.generic import DetailView

from core.utils import get_db_from_slug
from processos.models import Processo
from processos.services.checklist_service import ChecklistService


class ProcessoDetailView(DetailView):
    model = Processo
    template_name = "processos/processo_detail.html"
    context_object_name = "processo"

    def _get_db_ctx(self):
        slug = self.kwargs.get("slug")
        return {
            "slug": slug,
            "db_alias": get_db_from_slug(slug) if slug else "default",
            "empresa": self.request.session.get("empresa_id", 1),
            "filial": self.request.session.get("filial_id", 1),
        }

    def get_queryset(self):
        ctx = self._get_db_ctx()
        return (
            Processo.objects.using(ctx["db_alias"])
            .filter(proc_empr=ctx["empresa"], proc_fili=ctx["filial"])
            .select_related("proc_tipo")
        )

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        ctx = self._get_db_ctx()
        # idempotente — get_or_create internamente
        ChecklistService.gerar_respostas_para_processo(
            db_alias=ctx["db_alias"],
            empresa=ctx["empresa"],
            filial=ctx["filial"],
            processo=obj,
        )
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ctx = self._get_db_ctx()
        processo = context["processo"]

        respostas = (
            processo.respostas
            .using(ctx["db_alias"])
            .filter(pchr_empr=ctx["empresa"], pchr_fili=ctx["filial"])
            .select_related("pchr_item__chit_mode")
            .order_by("pchr_item__chit_orde")
        )

        modelo = ChecklistService.obter_modelo_ativo(
            db_alias=ctx["db_alias"],
            empresa=ctx["empresa"],
            filial=ctx["filial"],
            proc_tipo=processo.proc_tipo,
        )

        context["slug"] = ctx["slug"]
        context["respostas"] = respostas
        context["checklist_modelo"] = modelo
        context["checklist_versao"] = getattr(modelo, "chmo_vers", None)
        return context