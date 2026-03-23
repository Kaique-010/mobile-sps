from django.views.generic import ListView

from core.middleware import get_licenca_slug
from core.utils import get_licenca_db_config

from ...models import OrdemProducao


class OrdemProducaoListView(ListView):
    model = OrdemProducao
    template_name = "formulacao/ordem_list.html"
    context_object_name = "ordens"
    paginate_by = 20

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or "default"
        empresa_id = self.request.session.get("empresa_id", 1)
        filial_id = self.request.session.get("filial_id", 1)
        status_op = (self.request.GET.get("status") or "").strip().upper()[:1]

        qs = (
            OrdemProducao.objects.using(banco)
            .select_related("op_prod")
            .filter(op_empr=int(empresa_id), op_fili=int(filial_id))
        )
        if status_op:
            qs = qs.filter(op_status=status_op)
        return qs.order_by("-op_nume")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request) or "default"
        empresa_id = self.request.session.get("empresa_id", 1)
        filial_id = self.request.session.get("filial_id", 1)
        base_qs = OrdemProducao.objects.using(banco).filter(op_empr=int(empresa_id), op_fili=int(filial_id))

        context["slug"] = self.kwargs.get("slug") or get_licenca_slug()
        context["total_ops"] = base_qs.count()
        context["total_abertas"] = base_qs.filter(op_status="A").count()
        context["total_finalizadas"] = base_qs.filter(op_status="F").count()
        context["status"] = (self.request.GET.get("status") or "").strip().upper()[:1]
        return context
