from django.shortcuts import get_object_or_404, redirect, render
from core.utils import get_db_from_slug
from Pisos.models import Pedidospisos
from Pisos.web.forms import PedidoPisosForm


def editar_pedido_pisos(request, slug, pk):
    banco = get_db_from_slug(slug)
    pedido = get_object_or_404(Pedidospisos.objects.using(banco), pedi_nume=pk)
    if request.method == "POST":
        form = PedidoPisosForm(request.POST, instance=pedido)
        if form.is_valid():
            pedido_atualizado = form.save(commit=False)
            pedido_atualizado.save(using=banco)
            return redirect("PisosWeb:pedidos_pisos_visualizar", slug=slug, pk=pk)
    else:
        form = PedidoPisosForm(instance=pedido)
    return render(request, "Pisos/form.html", {"slug": slug, "form": form, "modo": "editar", "pedido": pedido})
