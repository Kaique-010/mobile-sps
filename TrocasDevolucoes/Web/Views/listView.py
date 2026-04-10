from django.views.generic import ListView

from core.utils import get_licenca_db_config
from TrocasDevolucoes.services.troca_devolucao_service import TrocaDevolucaoService
from Entidades.models import Entidades


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
        slug = (self.kwargs.get('slug') or getattr(getattr(self.request, 'resolver_match', None), 'kwargs', {}).get('slug'))    
        context['slug'] = self.kwargs.get('slug')
        banco = get_licenca_db_config(self.request)
        devolucoes = list(context.get('devolucoes') or [])
        pares = {(getattr(d, 'tdvl_empr', None), getattr(d, 'tdvl_clie', None)) for d in devolucoes}
        for empr, clie in pares:
            if empr is None or clie is None:
                continue
            row = (
                Entidades.objects.using(banco)
                .filter(enti_empr=empr, enti_clie=clie)
                .values('enti_nome')
                .first()
            )
            nome = row.get('enti_nome') if row else None
            for d in devolucoes:
                if getattr(d, 'tdvl_empr', None) == empr and getattr(d, 'tdvl_clie', None) == clie:
                    setattr(d, 'cliente_nome', nome)
        context['devolucoes'] = devolucoes
        return context
