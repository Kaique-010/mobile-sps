from django.contrib import messages
from django.shortcuts import redirect, render

from core.utils import get_db_from_slug
from Pisos.web.forms import PedidoPisosForm, ItemPedidoPisosFormSet
from Pisos.services.web_flow_service import PedidoPisosWebFlowService


def criar_pedido_pisos(request, slug):
    banco = get_db_from_slug(slug)
    form = PedidoPisosForm(request.POST or None)
    formset = ItemPedidoPisosFormSet(request.POST or None, prefix="itens")

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        itens = []
        for f in formset:
            if not f.cleaned_data or f.cleaned_data.get("DELETE"):
                continue
            item = {k: v for k, v in f.cleaned_data.items() if k != "DELETE"}
            if item.get("item_prod"):
                itens.append(item)

        payload = {**form.cleaned_data, "itens_input": itens}
        try:
            pedido = PedidoPisosWebFlowService.criar(banco, payload, request=request)
            messages.success(request, f"Pedido {pedido.pedi_nume} criado com sucesso.")
            return redirect("PisosWeb:pedidos_pisos_visualizar", slug=slug, pk=pedido.pedi_nume)
        except Exception as exc:
            messages.error(request, f"Erro ao criar pedido: {PedidoPisosWebFlowService.normalizar_erro(exc)}")

    return render(request, "Pisos/form.html", {"slug": slug, "form": form, "formset": formset, "modo": "criar"})
