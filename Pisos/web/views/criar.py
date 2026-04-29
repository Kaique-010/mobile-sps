import logging

from django.contrib import messages
from django.shortcuts import redirect, render

from core.utils import get_db_from_slug
from Pisos.web.forms import PedidoPisosForm, ItemPedidoPisosFormSet
from Pisos.services.web_flow_service import PedidoPisosWebFlowService


logger = logging.getLogger(__name__)


def criar_pedido_pisos(request, slug):
    banco = get_db_from_slug(slug)
    empresa_id = request.session.get("empresa_id")
    filial_id = request.session.get("filial_id")

    is_post = request.method == "POST"
    if is_post and (not empresa_id or not filial_id):
        messages.error(request, "Sessão inválida: empresa/filial não informadas.")
        form = PedidoPisosForm(None, initial={"pedi_empr": empresa_id, "pedi_fili": filial_id})
        formset = ItemPedidoPisosFormSet(None, prefix="itens")
        return render(request, "Pisos/form.html", {"slug": slug, "form": form, "formset": formset, "modo": "criar"})

    if is_post:
        post_data = request.POST.copy()
        post_data["pedi_empr"] = str(empresa_id)
        post_data["pedi_fili"] = str(filial_id)
        form = PedidoPisosForm(post_data, initial={"pedi_empr": empresa_id, "pedi_fili": filial_id})
        formset = ItemPedidoPisosFormSet(request.POST, prefix="itens")
    else:
        form = PedidoPisosForm(None, initial={"pedi_empr": empresa_id, "pedi_fili": filial_id})
        formset = ItemPedidoPisosFormSet(None, prefix="itens")

    is_form_valid = form.is_valid() if is_post else False
    is_formset_valid = formset.is_valid() if is_post else False

    if is_post and is_form_valid and is_formset_valid:
        itens = []
        for f in formset:
            if not f.cleaned_data or f.cleaned_data.get("DELETE"):
                continue
            item = {k: v for k, v in f.cleaned_data.items() if k != "DELETE"}
            if item.get("item_prod"):
                if not item.get("item_ambi"):
                    item["item_ambi"] = len(itens) + 1
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
            logger.exception("Erro ao criar pedido de pisos (slug=%s, banco=%s). Payload keys=%s", slug, banco, list(payload.keys()))
            messages.error(request, f"Erro ao criar pedido: {PedidoPisosWebFlowService.normalizar_erro(exc)}")

    if is_post and (not is_form_valid or not is_formset_valid):
        logger.warning(
            "Validação falhou ao criar pedido (slug=%s, banco=%s). form_errors=%s formset_errors=%s formset_non_form_errors=%s",
            slug,
            banco,
            form.errors.as_json(),
            [e for e in formset.errors],
            list(formset.non_form_errors()),
        )
        if form.errors:
            messages.error(request, f"Erros no formulário: {form.errors.as_text()}")
        if formset.non_form_errors():
            messages.error(request, f"Erros nos itens: {formset.non_form_errors()}")

    return render(request, "Pisos/form.html", {"slug": slug, "form": form, "formset": formset, "modo": "criar"})
