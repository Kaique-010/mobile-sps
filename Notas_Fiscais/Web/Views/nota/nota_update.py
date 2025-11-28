# notas_fiscais/views/nota/nota_update.py

from django.views.generic import UpdateView
from core.utils import get_licenca_db_config
from ....models import Nota
from ...forms import NotaForm, NotaItemFormSet, TransporteForm
from ....services.nota_service import NotaService
from ..base import SPSViewMixin


class NotaUpdateView(SPSViewMixin, UpdateView):
    model = Nota
    template_name = "notas/nota_form.html"
    form_class = NotaForm
    context_object_name = "nota"
    success_url_name = "nota_list"
    success_message = "Nota atualizada com sucesso."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        nota = self.object

        if self.request.POST:
            context["itens_formset"] = NotaItemFormSet(self.request.POST, instance=nota)
            context["transporte_form"] = TransporteForm(self.request.POST, instance=nota.transporte)
        else:
            context["itens_formset"] = NotaItemFormSet(instance=nota)
            context["transporte_form"] = TransporteForm(instance=nota.transporte)

        context["slug"] = self.kwargs.get("slug")

        return context

    def form_valid(self, form):
        context = self.get_context_data()
        itens_fs = context["itens_formset"]
        transporte_form = context["transporte_form"]

        if not itens_fs.is_valid() or not transporte_form.is_valid():
            return self.form_invalid(form)

        nota_data = form.cleaned_data
        itens = [f.cleaned_data for f in itens_fs if f.cleaned_data]
        transp = transporte_form.cleaned_data

        banco = get_licenca_db_config(self.request) or "default"

        NotaService.atualizar(
            nota=self.object,
            data=nota_data,
            itens=itens,
            impostos_map=None,
            transporte=transp,
            database=banco,
        )

        return self.form_success()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        banco = get_licenca_db_config(self.request) or "default"
        empresa = self.request.session.get("empresa_id")
        kwargs.update({"database": banco, "empresa_id": empresa})
        return kwargs
