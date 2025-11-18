from django.views.generic import TemplateView
from datetime import date, timedelta
from core.middleware import get_licenca_slug

class ExtratoMovimentacaoProdutosWebView(TemplateView):
    template_name = 'Gerencial/estoque_mov_dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            slug_val = self.kwargs.get('slug') or get_licenca_slug()
        except Exception:
            slug_val = self.kwargs.get('slug')

        empresa = self.request.session.get('empresa_id') or self.request.headers.get('X-Empresa') or self.request.GET.get('empr')
        filial = self.request.session.get('filial_id') or self.request.headers.get('X-Filial') or self.request.GET.get('fili')
        data_inicial = self.request.GET.get('data_ini')
        data_final = self.request.GET.get('data_fim')
        produto = self.request.GET.get('prod')

        if not data_inicial or not data_final:
            hoje = date.today()
            inicio = hoje - timedelta(days=30)
            data_inicial = data_inicial or inicio.strftime('%Y-%m-%d')
            data_final = data_final or hoje.strftime('%Y-%m-%d')

        ctx.update({
            'slug': slug_val,
            'filtros': {
                'empresa': empresa,
                'filial': filial,
                'data_inicial': data_inicial,
                'data_final': data_final,
                'produto': produto or '',
            }
        })
        return ctx