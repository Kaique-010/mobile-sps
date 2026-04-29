from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone

from core.utils import get_db_from_slug
from Pisos.web.forms import PedidoPisosForm, ItemPedidoPisosFormSet
from Pisos.services.web_flow_service import PedidoPisosWebFlowService


def criar_pedido_pisos(request, slug):
    banco = get_db_from_slug(slug)
    empresa_id = request.session.get("empresa_id")
    filial_id = request.session.get("filial_id")

    form = PedidoPisosForm(request.POST or None, initial={
        "pedi_empr": empresa_id,
        "pedi_fili": filial_id,
        "pedi_data": timezone.localdate(),
    })
    formset = ItemPedidoPisosFormSet(request.POST or None, prefix="itens")

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        if not empresa_id or not filial_id:
            messages.error(request, "Sessão inválida: empresa/filial não informadas.")
            return render(request, "Pisos/form.html", {"slug": slug, "form": form, "formset": formset, "modo": "criar"})

        itens = []
        for f in formset:
            if not f.cleaned_data or f.cleaned_data.get("DELETE"):
                continue
            item = {k: v for k, v in f.cleaned_data.items() if k != "DELETE"}
            if item.get("item_prod"):
                itens.append(item)

        payload = {
            **form.cleaned_data,
            "pedi_empr": empresa_id,
            "pedi_fili": filial_id,
            "itens_input": itens,
        }
        try:
            pedido = PedidoPisosWebFlowService.criar(banco, payload, request=request)
            messages.success(request, f"Pedido {pedido.pedi_nume} criado com sucesso.")
            return redirect("PisosWeb:pedidos_pisos_visualizar", slug=slug, pk=pedido.pedi_nume)
        except Exception as exc:
            messages.error(request, f"Erro ao criar pedido: {PedidoPisosWebFlowService.normalizar_erro(exc)}")

    return render(request, "Pisos/form.html", {"slug": slug, "form": form, "formset": formset, "modo": "criar"})
