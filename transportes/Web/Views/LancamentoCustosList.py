from django.db.models import Q, Count
from django.views.generic import ListView

from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.models import Custos


class LancamentoCustosListView(ListView):
    model = Custos
    template_name = "transportes/lancamento_custos_lista.html"
    context_object_name = "custos"
    paginate_by = 20

    def _get_banco(self):
        slug = self.kwargs.get("slug")
        return get_db_from_slug(slug) if slug else get_licenca_db_config(self.request)

    def get_queryset(self):
        banco = self._get_banco()
        empresa_id = self.request.session.get("empresa_id")
        filial_id = self.request.session.get("filial_id")

        qs = Custos.objects.using(banco).filter(lacu_empr=empresa_id)
        if filial_id:
            qs = qs.filter(lacu_fili=filial_id)

        term = (self.request.GET.get("q") or "").strip()
        if term:
            qs = qs.filter(
                Q(lacu_ctrl__icontains=term)
                | Q(lacu_frot__icontains=term)
                | Q(lacu_item__icontains=term)
                | Q(lacu_nome_item__icontains=term)
                | Q(lacu_docu__icontains=term)
            )

        lacu_data = self.request.GET.get("lacu_data")
        if lacu_data:
            qs = qs.filter(lacu_data=lacu_data)

        return qs.order_by("-lacu_data", "-lacu_ctrl")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["slug"] = self.kwargs.get("slug")
        context["titulo"] = "Lançamentos de Custos"
        qs = self.get_queryset()
        context["total_lancamentos"] = qs.count()

        totais_por_frota = (
            qs.exclude(lacu_frot__isnull=True)
            .exclude(lacu_frot="")
            .values("lacu_frot")
            .annotate(total=Count("lacu_ctrl"))
            .order_by("-total", "lacu_frot")
        )
        context["total_frotas"] = totais_por_frota.count()
        context["totais_por_frota"] = totais_por_frota
        context["top_frota"] = totais_por_frota.first()
        return context
