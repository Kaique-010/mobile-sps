from django.urls import reverse
from django.views.generic import DeleteView

from core.utils import get_db_from_slug
from processos.models import Processo


class ProcessoDeleteView(DeleteView):
    model = Processo

    def get_queryset(self):
        slug = self.kwargs.get("slug")
        db_alias = get_db_from_slug(slug) if slug else "default"
        empresa = self.request.session.get("empresa_id", 1)
        filial = self.request.session.get("filial_id", 1)
        return Processo.objects.using(db_alias).filter(proc_empr=empresa, proc_fili=filial)

    def get_success_url(self):
        return reverse("processos:lista", kwargs={"slug": self.kwargs.get("slug")})
