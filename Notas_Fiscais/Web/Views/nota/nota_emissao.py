from django.views.generic import TemplateView


class NotaEmissaoView(TemplateView):
    template_name = "notas/nota_emissao.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["slug"] = self.kwargs.get("slug")
        # Valores padrão de data podem ser setados aqui se necessário
        return ctx