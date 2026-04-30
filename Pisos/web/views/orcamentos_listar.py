from django.db.models import Sum
from django.views.generic import ListView

from core.utils import get_db_from_slug
from Pisos.models import Orcamentopisos
from Entidades.models import Entidades


class OrcamentoPisosListView(ListView):
    model = Orcamentopisos
    template_name = "Pisos/orcamentos_listar.html"
    context_object_name = "orcamentos"
    paginate_by = 50

    def get_queryset(self):
        self.banco = get_db_from_slug(self.kwargs["slug"])

        qs = (
            Orcamentopisos.objects
            .using(self.banco)
            .all()
            .order_by("-orca_nume")
        )
        
        numero = self.request.GET.get("orca_nume")
        cliente_nome = self.request.GET.get("cliente_nome")
        vendedor_nome = self.request.GET.get("vendedor_nome")
        status = self.request.GET.get("orca_stat")

        if numero:
            qs = qs.filter(orca_nume=numero)

        if status not in (None, ""):
            qs = qs.filter(orca_stat=status)

        if cliente_nome:
            clientes_ids = Entidades.objects.using(self.banco).filter(
                enti_nome__icontains=cliente_nome
            ).values_list("enti_clie", flat=True)

            qs = qs.filter(orca_clie__in=list(clientes_ids))

        if vendedor_nome:
            vendedores_ids = Entidades.objects.using(self.banco).filter(
                enti_nome__icontains=vendedor_nome
            ).values_list("enti_clie", flat=True)

            qs = qs.filter(orca_vend__in=list(vendedores_ids))  

        entidades_ids = set()

        for o in qs:
            if o.orca_clie:
                entidades_ids.add(o.orca_clie)
            if o.orca_vend:
                entidades_ids.add(o.orca_vend)

        entidades = Entidades.objects.using(self.banco).filter(
            enti_clie__in=entidades_ids
        )

        nomes = {
            e.enti_clie: e.enti_nome
            for e in entidades
        }

        for o in qs:
            o.cliente_nome = nomes.get(o.orca_clie, "")
            o.vendedor_nome = nomes.get(o.orca_vend, "")

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        base_qs = Orcamentopisos.objects.using(self.banco).all()

        context["slug"] = self.kwargs["slug"]
        context["metricas"] = {
            "total_orcamentos": base_qs.count(),
            "total_valor": base_qs.aggregate(total=Sum("orca_tota")).get("total") or 0,
            "total_exportados": base_qs.filter(orca_stat=2).count(),
            "total_cancelados": base_qs.filter(orca_stat=3).count(),
        }
        context["filtros"] = {
            "orca_nume": self.request.GET.get("orca_nume", ""),
            "cliente_nome": self.request.GET.get("cliente_nome", ""),
            "vendedor_nome": self.request.GET.get("vendedor_nome", ""),
            "orca_stat": self.request.GET.get("orca_stat", ""),
        }

        return context