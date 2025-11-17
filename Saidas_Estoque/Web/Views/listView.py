from django.views.generic import ListView
from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug
from Saidas_Estoque.models import SaidasEstoque


class SaidaListView(ListView):
    model = SaidasEstoque
    template_name = 'Saidas/saidas_listar.html'
    context_object_name = 'saidas'
    paginate_by = 50

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        return SaidasEstoque.objects.using(banco).all().order_by('-said_data', '-said_sequ')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug') or get_licenca_slug()
        return context