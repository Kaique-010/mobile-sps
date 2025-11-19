# notas_fiscais/views/nota/nota_list.py

from django.views.generic import ListView
from django.db.models import Q
from core.utils import get_licenca_db_config
from ....models import Nota


class NotaListView(ListView):
    model = Nota
    template_name = "notas/nota_list.html"
    context_object_name = "notas"
    paginate_by = 50

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or "default"
        empresa = self.request.session.get("empresa_id")
        filial = self.request.session.get("filial_id")

        qs = (
            Nota.objects.using(banco)
            .filter(empresa=empresa, filial=filial)
            .select_related("emitente", "destinatario")
            .prefetch_related("itens__impostos")
        )

        # Filtros
        status = (self.request.GET.get("status") or "").strip()
        cliente = (self.request.GET.get("cliente") or "").strip()
        data_ini = (self.request.GET.get("data_ini") or "").strip()
        data_fim = (self.request.GET.get("data_fim") or "").strip()

        if status:
            try:
                qs = qs.filter(status=int(status))
            except Exception:
                pass
        if cliente:
            qs = qs.filter(
                Q(destinatario__enti_nome__icontains=cliente)
                | Q(destinatario__enti_cnpj__icontains=cliente)
                | Q(destinatario__enti_cpf__icontains=cliente)
            )
        if data_ini:
            qs = qs.filter(data_emissao__gte=data_ini)
        if data_fim:
            qs = qs.filter(data_emissao__lte=data_fim)

        return qs.order_by("-data_emissao", "-numero")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["slug"] = self.kwargs.get("slug")
        ctx["status_choices"] = Nota._meta.get_field("status").choices
        ctx["preservado"] = {
            "status": (self.request.GET.get("status") or "").strip(),
            "cliente": (self.request.GET.get("cliente") or "").strip(),
            "data_ini": (self.request.GET.get("data_ini") or "").strip(),
            "data_fim": (self.request.GET.get("data_fim") or "").strip(),
        }
        return ctx
