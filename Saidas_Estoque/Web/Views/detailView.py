from django.views.generic import DetailView
from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug
from Saidas_Estoque.models import SaidasEstoque


class SaidaDetailView(DetailView):
    model = SaidasEstoque
    template_name = 'Saidas/saida_detalhe.html'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        return SaidasEstoque.objects.using(banco).all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug') or get_licenca_slug()
        return context