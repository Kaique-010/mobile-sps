from django.contrib import messages
from django.db import transaction
from django.db.models import Max
from django.shortcuts import redirect
from django.views.generic import TemplateView

from core.middleware import get_licenca_slug
from core.utils import get_licenca_db_config

from ..forms import FormulaItemAddForm
from ...models import FormulaItem, FormulaProduto


class FormulaEditView(TemplateView):
    template_name = "formulacao/formula_edit.html"

    def _get_db(self) -> str:
        return get_licenca_db_config(self.request) or "default"

    def _get_ids(self) -> tuple[int, int]:
        empresa_id = int(self.request.session.get("empresa_id", 1))
        filial_id = int(self.request.session.get("filial_id", 1))
        return empresa_id, filial_id

    def _get_formula(self):
        banco = self._get_db()
        empresa_id, filial_id = self._get_ids()
        return (
            FormulaProduto.objects.using(banco)
            .select_related("form_prod")
            .filter(id=int(self.kwargs.get("pk")), form_empr=empresa_id, form_fili=filial_id)
            .first()
        )

    def post(self, request, *args, **kwargs):
        banco = self._get_db()
        slug = self.kwargs.get("slug") or get_licenca_slug()
        empresa_id, filial_id = self._get_ids()

        formula = self._get_formula()
        if not formula:
            messages.error(self.request, "Fórmula não encontrada.")
            return redirect(f"/web/{slug}/formulacao/formulas/")

        action = (request.POST.get("action") or "").strip()

        try:
            with transaction.atomic(using=banco):
                if action == "toggle_ativ":
                    ativ = (request.POST.get("form_ativ") or "").lower() in ("1", "true", "t", "on", "sim", "s")
                    FormulaProduto.objects.using(banco).filter(id=formula.id).update(form_ativ=ativ)

                elif action == "add_item":
                    item_form = FormulaItemAddForm(
                        request.POST, database=banco, empresa_id=empresa_id
                    )
                    if not item_form.is_valid():
                        raise Exception("Dados inválidos para adicionar insumo.")

                    insu = item_form.cleaned_data["form_insu"]
                    qtde = item_form.cleaned_data["form_qtde"]
                    perd = item_form.cleaned_data.get("form_perd_perc")

                    max_item = (
                        FormulaItem.objects.using(banco)
                        .filter(form_form=formula)
                        .aggregate(m=Max("form_item"))
                        .get("m")
                        or 0
                    )
                    FormulaItem.objects.using(banco).create(
                        form_empr=empresa_id,
                        form_fili=filial_id,
                        form_form=formula,
                        form_insu=insu,
                        form_vers=int(formula.form_vers),
                        form_item=int(max_item) + 1,
                        form_qtde=qtde,
                        form_perd_perc=perd,
                    )

                elif action == "del_item":
                    item_id = int(request.POST.get("id") or 0)
                    if item_id:
                        FormulaItem.objects.using(banco).filter(id=item_id, form_form=formula).delete()

                elif action == "toggle_baixa_item":
                    item_id = int(request.POST.get("id") or 0)
                    baixar = (request.POST.get("baixar") or "").lower() in ("1", "true", "t", "on", "sim", "s")
                    if item_id:
                        FormulaItem.objects.using(banco).filter(id=item_id, form_form=formula).update(
                            form_baixa_estoque=baixar
                        )

                else:
                    raise Exception("Ação inválida.")

            messages.success(self.request, "Alterações salvas.")
        except Exception as e:
            messages.error(self.request, str(e))

        return redirect(f"/web/{slug}/formulacao/formulas/{formula.id}/")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = self._get_db()
        empresa_id, filial_id = self._get_ids()

        formula = self._get_formula()
        if not formula:
            context["formula"] = None
            return context

        itens = (
            FormulaItem.objects.using(banco)
            .filter(form_form=formula)
            .select_related("form_insu")
            .order_by("form_item")
        )

        context["slug"] = self.kwargs.get("slug") or get_licenca_slug()
        context["empresa_id"] = empresa_id
        context["filial_id"] = filial_id
        context["formula"] = formula
        context["itens"] = itens
        context["item_form"] = FormulaItemAddForm(database=banco, empresa_id=empresa_id)
        return context
