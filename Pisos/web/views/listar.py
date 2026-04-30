from django.db.models import Sum
from django.views.generic import ListView

from core.utils import get_db_from_slug
from Pisos.models import Pedidospisos
from Entidades.models import Entidades


class PedidopisosListView(ListView):
    template_name = "Pisos/listar.html"
    context_object_name = "pedidos"
    paginate_by = 50

    status_nome = {
        0: "Aberto",
        1: "Cancelado",
        2: "Fechado",
    }

    def get_queryset(self):
        self.banco = get_db_from_slug(self.kwargs["slug"])

        qs = (
            Pedidospisos.objects
            .using(self.banco)
            .all()
            .order_by("-pedi_nume")
        )

        numero = self.request.GET.get("pedi_nume")
        cliente_nome = self.request.GET.get("cliente_nome")
        vendedor_nome = self.request.GET.get("vendedor_nome")
        status = self.request.GET.get("pedi_stat")

        if numero:
            qs = qs.filter(pedi_nume=numero)

        if status not in (None, ""):
            qs = qs.filter(pedi_stat=status)

        if cliente_nome:
            clientes_ids = Entidades.objects.using(self.banco).filter(
                enti_nome__icontains=cliente_nome
            ).values_list("enti_clie", flat=True)

            qs = qs.filter(pedi_clie__in=list(clientes_ids))

        if vendedor_nome:
            vendedores_ids = Entidades.objects.using(self.banco).filter(
                enti_nome__icontains=vendedor_nome
            ).values_list("enti_clie", flat=True)

            qs = qs.filter(pedi_vend__in=list(vendedores_ids))

        entidades_ids = set()

        for p in qs:
            if p.pedi_clie:
                entidades_ids.add(p.pedi_clie)
            if p.pedi_vend:
                entidades_ids.add(p.pedi_vend)

        entidades = Entidades.objects.using(self.banco).filter(
            enti_clie__in=entidades_ids
        )

        nomes = {
            e.enti_clie: e.enti_nome
            for e in entidades
        }

        for p in qs:
            p.cliente_nome = nomes.get(p.pedi_clie, "")
            p.vendedor_nome = nomes.get(p.pedi_vend, "")
            p.status_nome = self.status_nome.get(p.pedi_stat, "")

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        base_qs = Pedidospisos.objects.using(self.banco).all()

        context["slug"] = self.kwargs["slug"]

        context["metricas"] = {
            "total_pedidos": base_qs.count(),
            "total_valor": base_qs.aggregate(total=Sum("pedi_tota")).get("total") or 0,
            "total_fechados": base_qs.filter(pedi_stat=2).count(),
            "total_abertos": base_qs.filter(pedi_stat=0).count(),
        }

        context["filtros"] = {
            "pedi_nume": self.request.GET.get("pedi_nume", ""),
            "cliente_nome": self.request.GET.get("cliente_nome", ""),
            "vendedor_nome": self.request.GET.get("vendedor_nome", ""),
            "pedi_stat": self.request.GET.get("pedi_stat", ""),
        }

        return context