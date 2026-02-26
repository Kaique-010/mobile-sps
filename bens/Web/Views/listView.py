from django.views.generic import ListView
from core.utils import get_licenca_db_config
from ..forms import BensptrForm
from ...models import Bensptr
from ...Web.Services.depreciacao_service import DepreciacaoService

class BensptrListView(ListView):
    model = Bensptr
    template_name = 'Bens/bens_list.html'
    context_object_name = 'bens'
    paginate_by = 20

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        qs = Bensptr.objects.using(banco).all()

        # Filtros
        codigo = self.request.GET.get('bens_codi')
        descricao = self.request.GET.get('bens_desc')
        grupo = self.request.GET.get('bens_grup')

        if codigo:
            qs = qs.filter(bens_codi__icontains=codigo)
        if descricao:
            qs = qs.filter(bens_desc__icontains=descricao)
        if grupo:
            qs = qs.filter(bens_grup=grupo)
            
        return qs.order_by('bens_codi')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Passar form para filtros (opcional, ou criar um form específico de filtro)
        # Aqui vamos passar apenas valores para manter no template se quiser
        return context
