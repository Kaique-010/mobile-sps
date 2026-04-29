from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from core.utils import get_db_from_slug
from Entidades.models import Entidades
from Pisos.models import Pedidospisos, Itenspedidospisos
from Pisos.web.forms import PedidoPisosForm, ItemPedidoPisosFormSet
from Pisos.services.web_flow_service import PedidoPisosWebFlowService


def editar_pedido_pisos(request, slug, pk):
    banco = get_db_from_slug(slug)
    pedido = get_object_or_404(Pedidospisos.objects.using(banco), pedi_nume=pk)

    cliente_label = ""
    if pedido.pedi_clie:
        ent = Entidades.objects.using(banco).filter(enti_clie=pedido.pedi_clie).first()
        if ent:
            cliente_label = f"{ent.enti_clie} - {ent.enti_nome}"

    vendedor_label = ""
    if pedido.pedi_vend:
        vend = Entidades.objects.using(banco).filter(enti_clie=pedido.pedi_vend).first()
        if vend:
            vendedor_label = f"{vend.enti_clie} - {vend.enti_nome}"

    initial_itens = []
    if request.method != "POST":
        for i in Itenspedidospisos.objects.using(banco).filter(item_empr=pedido.pedi_empr, item_fili=pedido.pedi_fili, item_pedi=pk).order_by("item_nume"):
            initial_itens.append({k: getattr(i, k) for k in ["item_ambi", "item_nome_ambi", "item_prod", "item_prod_nome", "item_m2", "item_quan", "item_caix", "item_unit", "item_suto", "item_desc", "item_queb", "item_obse"]})

    form = PedidoPisosForm(request.POST or None, instance=pedido)
    formset = ItemPedidoPisosFormSet(request.POST or None, prefix="itens", initial=initial_itens)

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
            PedidoPisosWebFlowService.atualizar(banco, pk, payload, request=request)
            messages.success(request, f"Pedido {pk} atualizado com sucesso.")
            return redirect("PisosWeb:pedidos_pisos_visualizar", slug=slug, pk=pk)
        except Exception as exc:
            messages.error(request, f"Erro ao atualizar pedido: {PedidoPisosWebFlowService.normalizar_erro(exc)}")

    return render(request, "Pisos/form.html", {"slug": slug, "form": form, "formset": formset, "modo": "editar", "pedido": pedido, "cliente_label": cliente_label, "vendedor_label": vendedor_label})
