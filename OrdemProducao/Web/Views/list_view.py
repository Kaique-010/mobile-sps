from django.views.generic import ListView

from ...models import Ordemproducao
from ...services import OrdemProducaoFilhosService, OrdemProducaoService
from .base import OrdemProducaoWebMixin
from django.core.paginator import Paginator


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
        ordens_qs = context.get('ordens')
        ordens = list(ordens_qs) if ordens_qs is not None else []
        entidade_ids = []
        for ordem in ordens:
            if ordem.orpr_clie:
                entidade_ids.append(ordem.orpr_clie)
            if ordem.orpr_vend:
                entidade_ids.append(ordem.orpr_vend)
        nomes = OrdemProducaoService.map_entidades_nomes(using=banco, empresa_id=empresa_id, entidade_ids=entidade_ids)
        status_labels = dict(Ordemproducao.status_ordem)
        tipo_labels = dict(Ordemproducao.tipo_ordem)
        for ordem in ordens:
            ordem.cliente_nome = nomes.get(int(ordem.orpr_clie)) if ordem.orpr_clie else None
            ordem.vendedor_nome = nomes.get(int(ordem.orpr_vend)) if ordem.orpr_vend else None
            ordem.tipo_label = tipo_labels.get(str(ordem.orpr_tipo), str(ordem.orpr_tipo or ''))
            ordem.status_label = status_labels.get(str(ordem.orpr_stat), str(ordem.orpr_stat or ''))

        context['dashboard'] = OrdemProducaoService.dashboard(using=banco)
        context['filtro_status'] = self.request.GET.get('status', '')
        context['filtro_tipo'] = self.request.GET.get('tipo', '')
        context['tipo_ordem'] = Ordemproducao.tipo_ordem
        ourives_qs = OrdemProducaoFilhosService.listar_ourives_master(using=banco, empresa_id=empresa_id)
        etapas_qs = OrdemProducaoFilhosService.listar_etapas_master(using=banco)
        ourives_page_num = int(self.request.GET.get('page_ourives') or 1)
        etapas_page_num = int(self.request.GET.get('page_etapas') or 1)
        ourives_paginator = Paginator(ourives_qs, 20)
        etapas_paginator = Paginator(etapas_qs, 20)
        ourives_page = ourives_paginator.get_page(ourives_page_num)
        etapas_page = etapas_paginator.get_page(etapas_page_num)
        context['ourives'] = list(ourives_page.object_list)
        context['etapas'] = list(etapas_page.object_list)
        context['ourives_page'] = ourives_page
        context['etapas_page'] = etapas_page
        return context
