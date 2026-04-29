from django.shortcuts import redirect, render
from core.utils import get_db_from_slug
from Pisos.web.forms import PedidoPisosForm


def criar_pedido_pisos(request, slug):
    banco = get_db_from_slug(slug)
    if request.method == "POST":
        form = PedidoPisosForm(request.POST)
        if form.is_valid():
            pedido = form.save(commit=False)
            pedido.save(using=banco)
            return redirect("PisosWeb:pedidos_pisos_visualizar", slug=slug, pk=pedido.pedi_nume)
    else:
        form = PedidoPisosForm()
    return render(request, "Pisos/form.html", {"slug": slug, "form": form, "modo": "criar"})
