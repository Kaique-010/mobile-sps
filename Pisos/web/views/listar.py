from django.shortcuts import render
from django.db.models import Sum
from core.utils import get_db_from_slug
from Pisos.models import Pedidospisos


def listar_pedidos_pisos(request, slug):
    banco = get_db_from_slug(slug)
    base_qs = Pedidospisos.objects.using(banco).all()
    metricas = {
        "total_pedidos": base_qs.count(),
        "total_valor": base_qs.aggregate(total=Sum("pedi_tota")).get("total") or 0,
        "total_fechados": base_qs.filter(pedi_stat=2).count(),
    }
    pedidos = base_qs.order_by("-pedi_nume")[:200]
    return render(request, "Pisos/listar.html", {"slug": slug, "pedidos": pedidos, "metricas": metricas})
