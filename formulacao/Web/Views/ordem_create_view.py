from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.db.models import Max
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import FormView

from core.middleware import get_licenca_slug
from core.utils import get_licenca_db_config
from Produtos.models import Lote, Produtos

from ..forms import OrdemProducaoForm
from ...models import FormulaItem, FormulaProduto, OrdemProducao


class OrdemProducaoCreateView(FormView):
    template_name = "formulacao/ordem_create.html"
    form_class = OrdemProducaoForm

    def get_success_url(self):
        slug = self.kwargs.get("slug") or get_licenca_slug()
        return f"/web/{slug}/formulacao/ordens/"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["database"] = get_licenca_db_config(self.request) or "default"
        kwargs["empresa_id"] = self.request.session.get("empresa_id", 1)
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        banco = get_licenca_db_config(self.request) or "default"
        empresa_id = self.request.session.get("empresa_id", 1)
        prod_codi = (self.request.GET.get("produto") or "").strip()
        vers = (self.request.GET.get("versao") or "").strip()

        initial["op_data"] = timezone.now().date()
        if prod_codi:
            prod = (
                Produtos.objects.using(banco)
                .filter(prod_empr=str(empresa_id), prod_codi=str(prod_codi))
                .first()
            )
            if prod:
                initial["op_prod"] = prod
        if vers.isdigit():
            initial["op_vers"] = int(vers)
        return initial

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or "default"
        empresa_id = int(self.request.session.get("empresa_id", 1))
        filial_id = int(self.request.session.get("filial_id", 1))

        def parse_date(value):
            if not value:
                return None
            if hasattr(value, "year"):
                return value
            try:
                return datetime.strptime(str(value), "%Y-%m-%d").date()
            except Exception:
                return None

        op_data = form.cleaned_data["op_data"]
        op_prod = form.cleaned_data["op_prod"]
        op_vers = int(form.cleaned_data["op_vers"])
        op_quan = form.cleaned_data["op_quan"]
        op_lote = (form.cleaned_data.get("op_lote") or "").strip() or None
        auto_lote = bool(form.cleaned_data.get("auto_lote"))
        lote_data_fabr = parse_date(self.request.POST.get("lote_data_fabr_ui"))
        lote_data_vali = parse_date(self.request.POST.get("lote_data_venc_ui"))

        try:
            with transaction.atomic(using=banco):
                max_nume = (
                    OrdemProducao.objects.using(banco)
                    .filter(op_empr=empresa_id, op_fili=filial_id)
                    .aggregate(m=Max("op_nume"))
                    .get("m")
                    or 0
                )
                op_nume = int(max_nume) + 1
                produto_codigo = str(op_prod.prod_codi)
                lote_numero = None

                raw_lote = (op_lote or "").strip()
                parts = [p.strip() for p in raw_lote.replace("_", "-").split("-") if p.strip()]
                candidato = next((p for p in reversed([raw_lote] + parts) if p.isdigit()), None)
                if candidato:
                    lote_numero = int(candidato)

                if auto_lote or not op_lote:
                    max_lote = (
                        Lote.objects.using(banco)
                        .filter(lote_empr=empresa_id, lote_prod=produto_codigo)
                        .aggregate(m=Max("lote_lote"))
                        .get("m")
                        or 0
                    )
                    lote_numero = int(max_lote) + 1
                    op_lote = str(lote_numero)

                OrdemProducao.objects.using(banco).create(
                    op_empr=empresa_id,
                    op_fili=filial_id,
                    op_nume=op_nume,
                    op_data=op_data,
                    op_prod=op_prod,
                    op_vers=op_vers,
                    op_quan=op_quan,
                    op_status="A",
                    op_lote=op_lote,
                )

                if lote_numero is not None:
                    qs_lote = Lote.objects.using(banco).filter(
                        lote_empr=empresa_id,
                        lote_prod=produto_codigo,
                        lote_lote=int(lote_numero),
                    )
                    if qs_lote.exists():
                        update = {"lote_ativ": True}
                        if lote_data_fabr:
                            update["lote_data_fabr"] = lote_data_fabr
                        if lote_data_vali:
                            update["lote_data_vali"] = lote_data_vali
                        if update:
                            qs_lote.update(**update)
                    else:
                        lote = Lote(
                            lote_empr=empresa_id,
                            lote_prod=produto_codigo,
                            lote_lote=int(lote_numero),
                            lote_unit=Decimal("0.00"),
                            lote_sald=Decimal("0.00"),
                            lote_data_fabr=lote_data_fabr,
                            lote_data_vali=lote_data_vali,
                            lote_ativ=True,
                        )
                        lote.save(using=banco)
            messages.success(self.request, f"Ordem {op_nume} criada com sucesso.")
            return redirect(self.get_success_url())
        except Exception as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request) or "default"
        empresa_id = int(self.request.session.get("empresa_id", 1))
        filial_id = int(self.request.session.get("filial_id", 1))
        prod_codi = (self.request.GET.get("produto") or "").strip()
        vers = (self.request.GET.get("versao") or "").strip()

        context["slug"] = self.kwargs.get("slug") or get_licenca_slug()
        context["empresa_id"] = empresa_id
        context["filial_id"] = filial_id
        context["lote_data_fabr_ui"] = ""
        context["lote_data_venc_ui"] = ""
        if self.request.method == "POST":
            context["lote_data_fabr_ui"] = (self.request.POST.get("lote_data_fabr_ui") or "").strip()
            context["lote_data_venc_ui"] = (self.request.POST.get("lote_data_venc_ui") or "").strip()

        context["formula"] = None
        context["insumos"] = []

        if prod_codi and vers.isdigit():
            formula = (
                FormulaProduto.objects.using(banco)
                .select_related("form_prod")
                .filter(
                    form_empr=empresa_id,
                    form_fili=filial_id,
                    form_prod__prod_codi=str(prod_codi),
                    form_vers=int(vers),
                    form_ativ=True,
                )
                .first()
            )
            if formula:
                context["formula"] = formula
                context["insumos"] = (
                    FormulaItem.objects.using(banco)
                    .filter(form_form=formula)
                    .select_related("form_insu")
                    .order_by("form_item")
                )

        return context
