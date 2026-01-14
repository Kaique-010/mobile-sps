# notas_fiscais/views/nota/nota_create.py

from django.views.generic import FormView
from datetime import date
from core.utils import get_licenca_db_config
from ....models import Nota
from ...forms import NotaForm, NotaItemFormSet, TransporteForm
from ....services.nota_service import NotaService
from ....services.calculo_impostos_service import CalculoImpostosService
from ..base import SPSViewMixin


class NotaCreateView(SPSViewMixin, FormView):
    template_name = "notas/nota_form.html"
    form_class = NotaForm
    success_url_name = "nota_list"
    success_message = "Nota criada com sucesso."

    def get_initial(self):
        initial = super().get_initial()
        hoje = date.today()
        initial.setdefault("data_emissao", hoje)
        initial.setdefault("data_saida", hoje)
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.POST:
            context["itens_formset"] = NotaItemFormSet(self.request.POST)
            context["transporte_form"] = TransporteForm(self.request.POST)
        else:
            context["itens_formset"] = NotaItemFormSet()
            context["transporte_form"] = TransporteForm()

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        banco = get_licenca_db_config(self.request) or "default"
        empresa = self.request.session.get("empresa_id")
        kwargs.update({"database": banco, "empresa_id": empresa})
        return kwargs

    def form_valid(self, form):
        context = self.get_context_data()
        itens_fs = context["itens_formset"]
        transporte_form = context["transporte_form"]

        if not itens_fs.is_valid() or not transporte_form.is_valid():
            return self.form_invalid(form)

        # Monta os dados
        nota_data = form.cleaned_data
        itens = [f.cleaned_data for f in itens_fs if f.cleaned_data]
        transporte = transporte_form.cleaned_data

        # Chama o service
        banco = get_licenca_db_config(self.request) or "default"
        empresa = self.request.session.get("empresa_id")
        filial = self.request.session.get("filial_id")

        nota = NotaService.criar(
            data=nota_data,
            itens=itens,
            impostos_map=None,
            transporte=transporte,
            empresa=empresa,
            filial=filial,
            database=banco,
        )

        CalculoImpostosService(banco).aplicar_impostos(nota)
        if nota:
            NotaService.gravar(nota, descricao="Rascunho criado via WEB")

        return self.form_success()
