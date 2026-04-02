from django.views.generic import ListView

from ...models import Ordemproducao
from ...services import OrdemProducaoFilhosService, OrdemProducaoService
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
        empresa_id = int(self.request.session.get('empresa_id') or 1)
        ordens = list(context.get('ordens') or [])
        entidade_ids = []
        for ordem in ordens:
            if ordem.orpr_clie:
                entidade_ids.append(ordem.orpr_clie)
            if ordem.orpr_vend:
                entidade_ids.append(ordem.orpr_vend)
        nomes = OrdemProducaoService.map_entidades_nomes(using=banco, empresa_id=empresa_id, entidade_ids=entidade_ids)
        for ordem in ordens:
            ordem.cliente_nome = nomes.get(int(ordem.orpr_clie)) if ordem.orpr_clie else None
            ordem.vendedor_nome = nomes.get(int(ordem.orpr_vend)) if ordem.orpr_vend else None

        context['dashboard'] = OrdemProducaoService.dashboard(using=banco)
        context['filtro_status'] = self.request.GET.get('status', '')
        context['filtro_tipo'] = self.request.GET.get('tipo', '')
        context['tipo_ordem'] = Ordemproducao.tipo_ordem
        context['ourives'] = OrdemProducaoFilhosService.listar_ourives_master(using=banco, empresa_id=empresa_id)
        context['etapas'] = OrdemProducaoFilhosService.listar_etapas_master(using=banco)
        return context
