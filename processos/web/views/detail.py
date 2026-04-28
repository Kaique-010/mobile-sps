from django.views.generic import DetailView

from core.utils import get_db_from_slug
from processos.models import Processo
from processos.services.checklist_service import ChecklistService


class ProcessoDetailView(DetailView):
    model = Processo
    template_name = "processos/processo_detail.html"
    context_object_name = "processo"

    def get_queryset(self):
        slug = self.kwargs.get("slug")
        db_alias = get_db_from_slug(slug) if slug else "default"
        empresa = self.request.session.get("empresa_id", 1)
        filial = self.request.session.get("filial_id", 1)
        return (
            Processo.objects.using(db_alias)
            .filter(proc_empr=empresa, proc_fili=filial)
            .select_related("proc_tipo")
            .prefetch_related("respostas__pchr_item")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs.get("slug")
        db_alias = get_db_from_slug(slug) if slug else "default"
        empresa = self.request.session.get("empresa_id", 1)
        filial = self.request.session.get("filial_id", 1)

        processo = context["processo"]
        resposta = processo.respostas.first()
        modelo = resposta.pchr_item.chit_mode if resposta else ChecklistService.obter_modelo_ativo(
            db_alias=db_alias,
            empresa=empresa,
            filial=filial,
            proc_tipo=processo.proc_tipo,
        )

        context["slug"] = slug
        context["checklist_modelo"] = modelo
        context["checklist_versao"] = getattr(modelo, "chmo_vers", None)
        return context
