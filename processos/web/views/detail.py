from django.views.generic import DetailView

from core.utils import get_db_from_slug
from processos.models import Processo


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
        context["slug"] = self.kwargs.get("slug")
        return context
