from django.views.generic import TemplateView
from datetime import date


class NotaEmissaoView(TemplateView):
    template_name = "notas/nota_emissao.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["slug"] = self.kwargs.get("slug")
        hoje = date.today().isoformat()
        ctx["data_emissao_default"] = hoje
        ctx["data_saida_default"] = hoje
        ctx["natureza_operacao_default"] = "Venda de mercadoria"
        ctx["natureza_operacao_opcoes"] = [
            {"value": "Venda de mercadoria", "label": "Venda de mercadoria"},
            {"value": "Venda de produção do estabelecimento", "label": "Venda de produção do estabelecimento"},
            {"value": "Devolução de venda", "label": "Devolução de venda"},
            {"value": "Remessa", "label": "Remessa"},
        ]
        return ctx
