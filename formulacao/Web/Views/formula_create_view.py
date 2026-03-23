from django.contrib import messages
from django.db import transaction
from django.db.models import Max
from django.shortcuts import redirect
from django.views.generic import FormView

from core.middleware import get_licenca_slug
from core.utils import get_licenca_db_config
from Produtos.models import Produtos

from ..forms import FormulaProdutoCreateForm
from ...models import FormulaProduto


class FormulaCreateView(FormView):
    template_name = "formulacao/formula_create.html"
    form_class = FormulaProdutoCreateForm

    def get_success_url(self):
        slug = self.kwargs.get("slug") or get_licenca_slug()
        return f"/web/{slug}/formulacao/formulas/"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["database"] = get_licenca_db_config(self.request) or "default"
        kwargs["empresa_id"] = self.request.session.get("empresa_id", 1)
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        banco = get_licenca_db_config(self.request) or "default"
        empresa_id = int(self.request.session.get("empresa_id", 1))
        filial_id = int(self.request.session.get("filial_id", 1))

        prod_codi = (self.request.GET.get("produto") or "").strip()
        if prod_codi:
            prod = (
                Produtos.objects.using(banco)
                .filter(prod_empr=str(empresa_id), prod_codi=str(prod_codi))
                .first()
            )
            if prod:
                initial["form_prod"] = prod
                max_vers = (
                    FormulaProduto.objects.using(banco)
                    .filter(form_empr=empresa_id, form_fili=filial_id, form_prod=prod)
                    .aggregate(m=Max("form_vers"))
                    .get("m")
                    or 0
                )
                initial["form_vers"] = int(max_vers) + 1
        return initial

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or "default"
        empresa_id = int(self.request.session.get("empresa_id", 1))
        filial_id = int(self.request.session.get("filial_id", 1))

        prod = form.cleaned_data["form_prod"]
        vers_raw = form.cleaned_data.get("form_vers")
        vers = int(vers_raw) if str(vers_raw or "").strip().isdigit() else 1
        ativ = bool(form.cleaned_data.get("form_ativ"))
        auto_vers = bool(form.cleaned_data.get("auto_vers"))

        try:
            with transaction.atomic(using=banco):
                if auto_vers:
                    max_vers = (
                        FormulaProduto.objects.using(banco)
                        .filter(form_empr=empresa_id, form_fili=filial_id, form_prod=prod)
                        .aggregate(m=Max("form_vers"))
                        .get("m")
                        or 0
                    )
                    vers = int(max_vers) + 1
                existe = (
                    FormulaProduto.objects.using(banco)
                    .filter(form_empr=empresa_id, form_fili=filial_id, form_prod=prod, form_vers=vers)
                    .exists()
                )
                if existe:
                    raise Exception("Já existe fórmula para este produto e versão.")

                formula = FormulaProduto.objects.using(banco).create(
                    form_empr=empresa_id,
                    form_fili=filial_id,
                    form_prod=prod,
                    form_vers=vers,
                    form_ativ=ativ,
                )
            messages.success(self.request, "Fórmula criada com sucesso.")
            return redirect(f"/web/{self.kwargs.get('slug') or get_licenca_slug()}/formulacao/formulas/{formula.id}/")
        except Exception as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["slug"] = self.kwargs.get("slug") or get_licenca_slug()
        context["empresa_id"] = int(self.request.session.get("empresa_id", 1))
        context["filial_id"] = int(self.request.session.get("filial_id", 1))
        return context
