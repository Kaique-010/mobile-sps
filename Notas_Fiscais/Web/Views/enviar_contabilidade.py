from django.contrib import messages
from django.urls import reverse
from django.views.generic import FormView

from core.utils import get_licenca_db_config

from ..forms import EnviarXmlContabilidadeForm
from ...services.gerar_xml_notas import gerar_e_enviar_xml_contabilidade


class EnviarXmlContabilidadeView(FormView):
    template_name = "notas/enviar_contabilidade.html"
    form_class = EnviarXmlContabilidadeForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["slug"] = self.kwargs.get("slug")
        return ctx

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or "default"
        slug = self.kwargs.get("slug")
        empresa = self.request.session.get("empresa_id")
        filial = self.request.session.get("filial_id")

        if not empresa or not filial:
            messages.error(self.request, "Selecione empresa e filial antes de enviar.")
            return self.form_invalid(form)

        raw = (form.cleaned_data.get("emails") or "").strip()
        emails = [e.strip() for e in raw.replace(",", ";").split(";") if e.strip()]
        if not emails:
            messages.error(self.request, "Informe ao menos um e-mail de destino.")
            return self.form_invalid(form)

        try:
            info = gerar_e_enviar_xml_contabilidade(
                empresa=int(empresa),
                filial=int(filial),
                periodo=(form.cleaned_data["data_inicio"], form.cleaned_data["data_fim"]),
                slug=slug,
                destinatarios=emails,
            )
        except Exception as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

        messages.success(self.request, f"{info['quantidade']} XML(s) enviado(s) com sucesso.")
        self.request.session["last_xml_contabilidade_db"] = banco
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("notas_enviar_contabilidade_web", kwargs={"slug": self.kwargs.get("slug")})

