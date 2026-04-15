from django.db.models import Q, Count
from django.views.generic import ListView

from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.models import Abastecusto


class AbastecimentosListView(ListView):
    model = Abastecusto
    template_name = "transportes/abastecimentos_lista.html"
    context_object_name = "abastecimentos"
    paginate_by = 20

    def _get_banco(self):
        slug = self.kwargs.get("slug")
        return get_db_from_slug(slug) if slug else get_licenca_db_config(self.request)

    def get_queryset(self):
        banco = self._get_banco()
        empresa_id = self.request.session.get("empresa_id")
        filial_id = self.request.session.get("filial_id")

        qs = Abastecusto.objects.using(banco).filter(abas_empr=empresa_id)
        if filial_id:
            qs = qs.filter(abas_fili=filial_id)

        term = (self.request.GET.get("q") or "").strip()
        if term:
            qs = qs.filter(
                Q(abas_ctrl__icontains=term)
                | Q(abas_frot__icontains=term)
                | Q(abas_bomb__icontains=term)
                | Q(abas_comb__icontains=term)
                | Q(abas_plac__icontains=term)
            )

        abas_data = self.request.GET.get("abas_data")
        if abas_data:
            qs = qs.filter(abas_data=abas_data)

        return qs.order_by("-abas_data", "-abas_ctrl")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Abastecimentos"
        qs = self.get_queryset()
        context["total_abastecimentos"] = qs.count()

        totais_por_frota = (
            qs.exclude(abas_frot__isnull=True)
            .exclude(abas_frot="")
            .values("abas_frot")
            .annotate(total=Count("abas_ctrl"))
            .order_by("-total", "abas_frot")
        )
        context["total_frotas"] = totais_por_frota.count()
        context["totais_por_frota"] = totais_por_frota
        context["top_frota"] = totais_por_frota.first()
        return context
