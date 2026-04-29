from django.shortcuts import render
from django.db.models import Sum
from core.utils import get_db_from_slug
from Pisos.models import Pedidospisos


def listar_pedidos_pisos(request, slug):
    banco = get_db_from_slug(slug)
    qs = Pedidospisos.objects.using(banco).all().order_by("-pedi_nume")[:200]
    metricas = {
        "total_pedidos": qs.count(),
        "total_valor": qs.aggregate(total=Sum("pedi_tota")).get("total") or 0,
        "total_fechados": qs.filter(pedi_stat=2).count(),
    }
    return render(request, "Pisos/listar.html", {"slug": slug, "pedidos": qs, "metricas": metricas})
