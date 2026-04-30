import logging

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from core.utils import get_db_from_slug
from Pisos.models import Itensorcapisos, Orcamentopisos
from Pisos.services.orcamento_atualizar_service import OrcamentoAtualizarService
from Pisos.services.orcamento_exportar_service import OrcamentoExportarPedidoService
from Pisos.web.forms import ItemOrcamentoPisosFormSet, OrcamentoPisosForm


logger = logging.getLogger(__name__)


def editar_orcamento_pisos(request, slug, pk):
    banco = get_db_from_slug(slug)
    orcamento = get_object_or_404(Orcamentopisos.objects.using(banco), orca_nume=pk)

    initial_itens = []
    if request.method != "POST":
        for i in Itensorcapisos.objects.using(banco).filter(
            item_empr=orcamento.orca_empr,
            item_fili=orcamento.orca_fili,
            item_orca=orcamento.orca_nume,
        ).order_by("item_nume", "item_ambi"):
            initial_itens.append({k: getattr(i, k) for k in ["item_ambi", "item_nome_ambi", "item_prod", "item_m2", "item_quan", "item_caix", "item_unit", "item_suto", "item_desc", "item_queb", "item_obse"]})

    is_post = request.method == "POST"
    if is_post:
        post_data = request.POST.copy()
        post_data["orca_empr"] = str(orcamento.orca_empr)
        post_data["orca_fili"] = str(orcamento.orca_fili)
        form = OrcamentoPisosForm(post_data, instance=orcamento)
        formset = ItemOrcamentoPisosFormSet(request.POST, prefix="itens", initial=initial_itens)
    else:
        form = OrcamentoPisosForm(None, instance=orcamento)
        formset = ItemOrcamentoPisosFormSet(None, prefix="itens", initial=initial_itens)

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
            "orca_empr": orcamento.orca_empr,
            "orca_fili": orcamento.orca_fili,
            "itens_input": itens,
        }
        try:
            OrcamentoAtualizarService().executar(
                banco=banco,
                orcamento=orcamento,
                dados=form.cleaned_data,
                itens=itens,
            )
            if request.POST.get("acao") == "exportar":
                pedido_numero = OrcamentoExportarPedidoService().executar(
                    banco=banco,
                    empresa=orcamento.orca_empr,
                    filial=orcamento.orca_fili,
                    numero=orcamento.orca_nume,
                )   
                messages.success(request, f"Orçamento {pk} exportado para pedido {pedido_numero}.")
                return redirect("PisosWeb:pedidos_pisos_visualizar", slug=slug, pk=pedido_numero)
            messages.success(request, f"Orçamento {pk} atualizado com sucesso.")
            return redirect("PisosWeb:orcamentos_pisos_visualizar", slug=slug, pk=pk)
        except Exception as exc:
            logger.exception("Erro ao atualizar orçamento de pisos (slug=%s, banco=%s, orca=%s).", slug, banco, pk)
            messages.error(request, f"Erro ao atualizar orçamento: {OrcamentoAtualizarService.normalizar_erro(exc)}")

    if is_post and (not is_form_valid or not is_formset_valid):
        logger.warning(
            "Validação falhou ao editar orçamento (slug=%s, banco=%s, orca=%s). form_errors=%s formset_errors=%s formset_non_form_errors=%s",
            slug,
            banco,
            pk,
            form.errors.as_json(),
            [e for e in formset.errors],
            list(formset.non_form_errors()),
        )

    return render(request, "Pisos/orcamento_form.html", {"slug": slug, "form": form, "formset": formset, "modo": "editar", "orcamento": orcamento})

