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
from Produtos.models import Lote, Tabelaprecos

from ..forms import OrdemProducaoEditForm
from ...models import FormulaItem, FormulaProduto, OrdemProducao


class OrdemProducaoEditView(FormView):
    template_name = "formulacao/ordem_edit.html"
    form_class = OrdemProducaoEditForm

    def _get_db(self) -> str:
        return get_licenca_db_config(self.request) or "default"

    def _get_ids(self) -> tuple[int, int]:
        empresa_id = int(self.request.session.get("empresa_id", 1))
        filial_id = int(self.request.session.get("filial_id", 1))
        return empresa_id, filial_id

    def _get_op(self):
        banco = self._get_db()
        empresa_id, filial_id = self._get_ids()
        pk = int(self.kwargs.get("pk"))
        return (
            OrdemProducao.objects.using(banco)
            .select_related("op_prod")
            .filter(op_empr=empresa_id, op_fili=filial_id, op_nume=pk)
            .first()
        )

    def get_success_url(self):
        slug = self.kwargs.get("slug") or get_licenca_slug()
        return f"/web/{slug}/formulacao/ordens/"

    def get_initial(self):
        initial = super().get_initial()
        banco = self._get_db()
        empresa_id, filial_id = self._get_ids()

        op = self._get_op()
        if not op:
            return initial

        initial["op_data"] = op.op_data or timezone.now().date()
        initial["op_quan"] = op.op_quan
        initial["op_lote"] = op.op_lote

        tabela = (
            Tabelaprecos.objects.using(banco)
            .filter(tabe_empr=empresa_id, tabe_fili=filial_id, tabe_prod=str(op.op_prod.prod_codi))
            .first()
        )
        if tabela:
            initial["preco_vista"] = getattr(tabela, "tabe_avis", None)
            initial["preco_prazo"] = getattr(tabela, "tabe_apra", None)

        return initial

    def form_valid(self, form):
        banco = self._get_db()
        empresa_id, filial_id = self._get_ids()
        slug = self.kwargs.get("slug") or get_licenca_slug()

        op = self._get_op()
        if not op:
            messages.error(self.request, "Ordem não encontrada.")
            return redirect(self.get_success_url())

        if op.op_status != "A":
            messages.error(self.request, "Apenas ordens abertas podem ser editadas.")
            return redirect(self.get_success_url())

        op_data = form.cleaned_data["op_data"]
        op_quan = form.cleaned_data["op_quan"]
        op_lote = (form.cleaned_data.get("op_lote") or "").strip() or None
        auto_lote = bool(form.cleaned_data.get("auto_lote"))
        preco_vista = form.cleaned_data.get("preco_vista")
        preco_prazo = form.cleaned_data.get("preco_prazo")

        def parse_date(value):
            if not value:
                return None
            if hasattr(value, "year"):
                return value
            try:
                return datetime.strptime(str(value), "%Y-%m-%d").date()
            except Exception:
                return None

        lote_data_fabr = parse_date(self.request.POST.get("lote_data_fabr_ui"))
        lote_data_vali = parse_date(self.request.POST.get("lote_data_venc_ui"))

        try:
            with transaction.atomic(using=banco):
                produto_codigo = str(op.op_prod.prod_codi)
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

                OrdemProducao.objects.using(banco).filter(
                    op_empr=empresa_id, op_fili=filial_id, op_nume=op.op_nume
                ).update(
                    op_data=op_data,
                    op_quan=op_quan,
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

                if preco_vista is not None or preco_prazo is not None:
                    chave = {
                        "tabe_empr": empresa_id,
                        "tabe_fili": filial_id,
                        "tabe_prod": str(op.op_prod.prod_codi),
                    }
                    update_fields = {}
                    if preco_vista is not None:
                        update_fields["tabe_avis"] = preco_vista
                    if preco_prazo is not None:
                        update_fields["tabe_apra"] = preco_prazo

                    qs = Tabelaprecos.objects.using(banco).filter(**chave)
                    if qs.exists():
                        qs.update(**update_fields)
                    else:
                        Tabelaprecos.objects.using(banco).create(**{**chave, **update_fields})

            messages.success(self.request, "Ordem atualizada.")
            return redirect(f"/web/{slug}/formulacao/ordens/{op.op_nume}/editar/")
        except Exception as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = self._get_db()
        empresa_id, filial_id = self._get_ids()

        op = self._get_op()
        context["slug"] = self.kwargs.get("slug") or get_licenca_slug()
        context["empresa_id"] = empresa_id
        context["filial_id"] = filial_id
        context["op"] = op
        context["lote_data_fabr"] = None
        context["lote_data_vali"] = None

        context["formula"] = None
        context["insumos"] = []

        if op:
            raw_lote = (op.op_lote or "").strip()
            parts = [p.strip() for p in raw_lote.replace("_", "-").split("-") if p.strip()]
            candidato = next((p for p in reversed([raw_lote] + parts) if p.isdigit()), None)
            lote_numero = int(candidato) if candidato else None
            produto_codigo = str(op.op_prod.prod_codi)

            if lote_numero is not None:
                row = (
                    Lote.objects.using(banco)
                    .filter(
                        lote_empr=empresa_id,
                        lote_prod=produto_codigo,
                        lote_lote=int(lote_numero),
                    )
                    .values("lote_data_fabr", "lote_data_vali")
                    .first()
                )
                if row:
                    context["lote_data_fabr"] = row.get("lote_data_fabr")
                    context["lote_data_vali"] = row.get("lote_data_vali")

            formula = (
                FormulaProduto.objects.using(banco)
                .select_related("form_prod")
                .filter(
                    form_empr=empresa_id,
                    form_fili=filial_id,
                    form_prod=op.op_prod,
                    form_vers=int(op.op_vers),
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
