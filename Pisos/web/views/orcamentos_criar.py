import logging

from django.contrib import messages
from django.shortcuts import redirect, render

from core.utils import get_db_from_slug
from Pisos.services.web_flow_service import OrcamentoPisosWebFlowService, exportar_orcamento_para_pedido
from Pisos.web.forms import ItemOrcamentoPisosFormSet, OrcamentoPisosForm


logger = logging.getLogger(__name__)


def criar_orcamento_pisos(request, slug):
    banco = get_db_from_slug(slug)
    empresa_id = request.session.get("empresa_id")
    filial_id = request.session.get("filial_id")

    is_post = request.method == "POST"
    if is_post and (not empresa_id or not filial_id):
        messages.error(request, "Sessão inválida: empresa/filial não informadas.")
        form = OrcamentoPisosForm(None, initial={"orca_empr": empresa_id, "orca_fili": filial_id})
        formset = ItemOrcamentoPisosFormSet(None, prefix="itens")
        return render(request, "Pisos/orcamento_form.html", {"slug": slug, "form": form, "formset": formset, "modo": "criar"})

    if is_post:
        post_data = request.POST.copy()
        post_data["orca_empr"] = str(empresa_id)
        post_data["orca_fili"] = str(filial_id)
        form = OrcamentoPisosForm(post_data, initial={"orca_empr": empresa_id, "orca_fili": filial_id})
        formset = ItemOrcamentoPisosFormSet(request.POST, prefix="itens")
    else:
        form = OrcamentoPisosForm(None, initial={"orca_empr": empresa_id, "orca_fili": filial_id})
        formset = ItemOrcamentoPisosFormSet(None, prefix="itens")

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
            "orca_empr": empresa_id,
            "orca_fili": filial_id,
            "itens_input": itens,
        }
        try:
            orcamento = OrcamentoPisosWebFlowService.criar(banco, payload, request=request)
            if request.POST.get("acao") == "exportar":
                pedido_numero = exportar_orcamento_para_pedido(banco, orcamento.orca_empr, orcamento.orca_fili, orcamento.orca_nume)
                messages.success(request, f"Orçamento {orcamento.orca_nume} exportado para pedido {pedido_numero}.")
                return redirect("PisosWeb:pedidos_pisos_visualizar", slug=slug, pk=pedido_numero)
            messages.success(request, f"Orçamento {orcamento.orca_nume} criado com sucesso.")
            return redirect("PisosWeb:orcamentos_pisos_visualizar", slug=slug, pk=orcamento.orca_nume)
        except Exception as exc:
            logger.exception("Erro ao criar orçamento de pisos (slug=%s, banco=%s). Payload keys=%s", slug, banco, list(payload.keys()))
            messages.error(request, f"Erro ao criar orçamento: {OrcamentoPisosWebFlowService.normalizar_erro(exc)}")

    if is_post and (not is_form_valid or not is_formset_valid):
        logger.warning(
            "Validação falhou ao criar orçamento (slug=%s, banco=%s). form_errors=%s formset_errors=%s formset_non_form_errors=%s",
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

    return render(request, "Pisos/orcamento_form.html", {"slug": slug, "form": form, "formset": formset, "modo": "criar"})

