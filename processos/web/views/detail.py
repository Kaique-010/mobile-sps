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
        )

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        slug = self.kwargs.get("slug")
        db_alias = get_db_from_slug(slug) if slug else "default"
        empresa = self.request.session.get("empresa_id", 1)
        filial = self.request.session.get("filial_id", 1)

        # Garante que as respostas existam (idempotente via get_or_create)
        ChecklistService.gerar_respostas_para_processo(
            db_alias=db_alias,
            empresa=empresa,
            filial=filial,
            processo=obj,
        )
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs.get("slug")
        db_alias = get_db_from_slug(slug) if slug else "default"
        empresa = self.request.session.get("empresa_id", 1)
        filial = self.request.session.get("filial_id", 1)

        # Busca as respostas explicitamente com o banco correto
        context["respostas"] = (
            self.object.respostas
            .using(db_alias)
            .filter(pchr_empr=empresa, pchr_fili=filial)
            .select_related("pchr_item")
            .order_by("pchr_item__chit_orde")
        )
        context["slug"] = slug
        return context