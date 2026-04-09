from django.views.generic import ListView

from core.utils import get_licenca_db_config
from TrocasDevolucoes.services.troca_devolucao_service import TrocaDevolucaoService


class DevolucoesListView(ListView):
    template_name = 'TrocasDevolucoes/devolucoes_listar.html'
    context_object_name = 'devolucoes'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        filtros = {
            'tdvl_empr': self.request.GET.get('tdvl_empr'),
            'tdvl_fili': self.request.GET.get('tdvl_fili'),
            'tdvl_stat': self.request.GET.get('tdvl_stat'),
        }
        return TrocaDevolucaoService.listar(banco, filtros=filtros)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')
        return context
