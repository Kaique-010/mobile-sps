from django.db.models import Sum
from django.shortcuts import render

from core.utils import get_db_from_slug
from Pisos.models import Orcamentopisos


def listar_orcamentos_pisos(request, slug):
    banco = get_db_from_slug(slug)
    base_qs = Orcamentopisos.objects.using(banco).all()
    metricas = {
        "total_orcamentos": base_qs.count(),
        "total_valor": base_qs.aggregate(total=Sum("orca_tota")).get("total") or 0,
        "total_exportados": base_qs.filter(orca_stat=2).count(),
    }
    orcamentos = base_qs.order_by("-orca_nume")[:200]
    return render(request, "Pisos/orcamentos_listar.html", {"slug": slug, "orcamentos": orcamentos, "metricas": metricas})

