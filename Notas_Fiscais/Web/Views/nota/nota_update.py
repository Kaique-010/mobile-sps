import logging

from django.views.generic import UpdateView
from django.urls import reverse
from core.utils import get_licenca_db_config
from ....models import Nota
from ...forms import NotaForm, NotaItemFormSet, TransporteForm
from ....services.nota_service import NotaService
from ....dominio.builder import NotaBuilder
from ..base import SPSViewMixin


logger = logging.getLogger(__name__)


class NotaUpdateView(SPSViewMixin, UpdateView):
    model = Nota
    template_name = "notas/nota_form.html"
    form_class = NotaForm
    context_object_name = "nota"
    def get_success_url(self):
        slug = self.kwargs.get("slug")
        return reverse("NotasFiscaisWeb:nota_list", kwargs={"slug": slug})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        nota = self.object
        try:
            transp_instance = nota.transporte
        except Nota.transporte.RelatedObjectDoesNotExist:
            transp_instance = None

        if self.request.POST:
            context["itens_formset"] = NotaItemFormSet(self.request.POST, instance=nota)
            context["transporte_form"] = TransporteForm(self.request.POST, instance=transp_instance)
        else:
            context["itens_formset"] = NotaItemFormSet(instance=nota)
            context["transporte_form"] = TransporteForm(instance=transp_instance)

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
        transp = transporte_form.cleaned_data if transporte_form.has_changed() else None

        banco = get_licenca_db_config(self.request) or "default"

        nota = NotaService.atualizar(
            nota=self.object,
            data=nota_data,
            itens=itens,
            impostos_map=None,
            transporte=transp,
            database=banco,
        )

        try:
            empresa = self.request.session.get("empresa_id")
            filial = self.request.session.get("filial_id")
            dto = NotaBuilder(nota, database=banco).build()
            dto_payload = dto.dict()
            logger.debug(
                "NotaUpdateView.form_valid: DTO base para geração de XML da nota %s (empresa=%s, filial=%s): %s",
                nota.pk,
                empresa,
                filial,
                dto_payload,
            )
        except Exception as e:
            logger.warning("NotaUpdateView.form_valid: falha ao montar DTO para nota %s: %s", self.object.pk, e)

        return self.form_success()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        banco = get_licenca_db_config(self.request) or "default"
        empresa = self.request.session.get("empresa_id")
        kwargs.update({"database": banco, "empresa_id": empresa})
        return kwargs
