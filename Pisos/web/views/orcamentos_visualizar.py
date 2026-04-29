from django.shortcuts import get_object_or_404, render

from core.utils import get_db_from_slug
from Pisos.models import Itensorcapisos, Orcamentopisos


def visualizar_orcamento_pisos(request, slug, pk):
    banco = get_db_from_slug(slug)
    orcamento = get_object_or_404(Orcamentopisos.objects.using(banco), orca_nume=pk)
    itens = Itensorcapisos.objects.using(banco).filter(
        item_empr=orcamento.orca_empr,
        item_fili=orcamento.orca_fili,
        item_orca=orcamento.orca_nume,
    ).order_by("item_nume", "item_ambi")
    return render(request, "Pisos/orcamento_visualizar.html", {"slug": slug, "orcamento": orcamento, "itens": itens})

