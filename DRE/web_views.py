from django.views.generic import TemplateView
from core.middleware import get_licenca_slug


class DREDashboardView(TemplateView):
    template_name = 'DRE/dre_dashboard.html'

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

        ctx.update({
            'slug': slug_val,
            'filtros': {
                'empresa': empresa,
                'filial': filial,
                'data_inicial': data_inicial,
                'data_final': data_final,
            }
        })
        return ctx