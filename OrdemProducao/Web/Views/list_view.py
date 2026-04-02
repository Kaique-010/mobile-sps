from django.views.generic import ListView

from ...models import Ordemproducao
from ...services import OrdemProducaoService
from .base import OrdemProducaoWebMixin


class OrdemproducaoListView(OrdemProducaoWebMixin, ListView):
    model = Ordemproducao
    template_name = 'OrdemProducao/ordemproducao_list.html'
    context_object_name = 'ordens'
    paginate_by = 20

    def get_queryset(self):
        banco = self.get_banco()
        qs = OrdemProducaoService.listar_ordens(using=banco)

        status = self.request.GET.get('status')
        tipo = self.request.GET.get('tipo')
        if status:
            qs = qs.filter(orpr_stat=status)
        if tipo:
            qs = qs.filter(orpr_tipo=tipo)
        return qs.order_by('-orpr_codi')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = self.get_banco()
        context['dashboard'] = OrdemProducaoService.dashboard(using=banco)
        context['filtro_status'] = self.request.GET.get('status', '')
        context['filtro_tipo'] = self.request.GET.get('tipo', '')
        context['tipo_ordem'] = Ordemproducao.tipo_ordem
        return context
