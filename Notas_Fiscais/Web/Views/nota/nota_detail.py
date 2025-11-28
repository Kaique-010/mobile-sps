# notas_fiscais/views/nota/nota_detail.py

from django.views.generic import DetailView
from core.utils import get_licenca_db_config
from ....models import Nota
from Licencas.models import Filiais
from Entidades.models import Entidades


class NotaDetailView(DetailView):
    model = Nota
    template_name = "notas/nota_detail.html"
    context_object_name = "nota"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request) or "default"
        nota: Nota = ctx.get("nota")
        emitente = Filiais.objects.using(banco).get(empr_empr=nota.empresa, empr_codi=nota.filial)
        destinatario = Entidades.objects.using(banco).get(enti_empr=nota.empresa, enti_clie=nota.destinatario_id)
        ctx["emitente"] = emitente
        ctx["destinatario"] = destinatario
        ctx["slug"] = self.kwargs.get("slug")
        return ctx
