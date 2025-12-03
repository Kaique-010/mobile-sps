from django.views.generic import ListView
from ..mixin import DBAndSlugMixin
from django.utils import timezone
from django.utils.http import urlencode
from django.db.models import Sum, Q
from django.http import JsonResponse
from core.utils import get_licenca_db_config
from ...models import Titulosreceber, Baretitulos
from Entidades.models import Entidades


class TitulosReceberListView(DBAndSlugMixin, ListView):
    model = Titulosreceber
    template_name = 'ContasAReceber/titulos_receber_list.html'
    context_object_name = 'titulos'
    paginate_by = 20

    def get_queryset(self):
        qs = Titulosreceber.objects.using(self.db_alias).all()
        data_min = '1900-01-01'
        data_max = '2100-12-31'
        qs = qs.filter(
            Q(titu_emis__isnull=True) | Q(titu_emis__range=(data_min, data_max)),
            Q(titu_venc__isnull=True) | Q(titu_venc__range=(data_min, data_max)),
        ).only('titu_empr','titu_fili','titu_clie','titu_titu','titu_seri','titu_parc','titu_valo','titu_venc','titu_emis','titu_aber')

        cliente_id = self.request.GET.get('titu_clie')
        cliente_nome = self.request.GET.get('cliente_nome')
        status_aber = self.request.GET.get('titu_aber')
        venc_ini = self.request.GET.get('venc_ini')
        venc_fim = self.request.GET.get('venc_fim')
        parcela = self.request.GET.get('titu_parc')
        serie = self.request.GET.get('titu_seri')

        if self.empresa_id:
            qs = qs.filter(titu_empr=self.empresa_id)
        if self.filial_id:
            qs = qs.filter(titu_fili=self.filial_id)
        if cliente_id:
            qs = qs.filter(titu_clie=cliente_id)
        if status_aber:
            qs = qs.filter(titu_aber=status_aber)
        if venc_ini:
            qs = qs.filter(titu_venc__gte=venc_ini)
        if parcela:
            qs = qs.filter(titu_parc=parcela)
        if venc_fim:
            qs = qs.filter(titu_venc__lte=venc_fim)
        if serie:
            qs = qs.filter(titu_seri__iexact=serie)

        if cliente_nome:
            entidades_qs = Entidades.objects.using(self.db_alias).filter(enti_nome__icontains=cliente_nome)
            cliente_ids = list(entidades_qs.values_list('enti_clie', flat=True))
            if cliente_ids:
                qs = qs.filter(titu_clie__in=cliente_ids)
            else:
                qs = qs.none()

        return qs.order_by('titu_venc', 'titu_titu', 'titu_parc')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_qs = context.get('titulos')
        cliente_ids = set()
        for t in page_qs:
            if t.titu_clie:
                cliente_ids.add(t.titu_clie)

        entidades_map = {}
        if cliente_ids:
            ents = Entidades.objects.using(self.db_alias).filter(enti_clie__in=list(cliente_ids))
            entidades_map = {e.enti_clie: e.enti_nome for e in ents}

        for t in page_qs:
            setattr(t, 'cliente_nome', entidades_map.get(t.titu_clie, ''))

        preserved = {
            'titu_clie': self.request.GET.get('titu_clie') or '',
            'titu_parc': self.request.GET.get('titu_parc') or '',
            'cliente_nome': self.request.GET.get('cliente_nome') or '',
            'titu_aber': self.request.GET.get('titu_aber') or '',
            'venc_ini': self.request.GET.get('venc_ini') or '',
            'venc_fim': self.request.GET.get('venc_fim') or '',
            'titu_seri': self.request.GET.get('titu_seri') or '',
        }
        preserved_qs = {k: v for k, v in preserved.items() if v}

        # Cálculo dos indicadores de resumo (Total Recebido, Em Aberto, Percentuais)
        qs_total = Titulosreceber.objects.using(self.db_alias).all()
        data_min = '1900-01-01'
        data_max = '2100-12-31'
        qs_total = qs_total.filter(
            Q(titu_emis__isnull=True) | Q(titu_emis__range=(data_min, data_max)),
            Q(titu_venc__isnull=True) | Q(titu_venc__range=(data_min, data_max)),
        )
        if self.empresa_id:
            qs_total = qs_total.filter(titu_empr=self.empresa_id)
        if self.filial_id:
            qs_total = qs_total.filter(titu_fili=self.filial_id)
        if preserved['titu_clie']:
            qs_total = qs_total.filter(titu_clie=preserved['titu_clie'])
        if preserved['titu_aber']:
            qs_total = qs_total.filter(titu_aber=preserved['titu_aber'])
        if preserved['venc_ini']:
            qs_total = qs_total.filter(titu_venc__gte=preserved['venc_ini'])
        if preserved['venc_fim']:
            qs_total = qs_total.filter(titu_venc__lte=preserved['venc_fim'])
        if preserved['titu_parc']:
            qs_total = qs_total.filter(titu_parc=preserved['titu_parc'])

        total_geral = qs_total.aggregate(total=Sum('titu_valo'))['total'] or 0
        total_quitado = qs_total.filter(titu_aber='T').aggregate(total=Sum('titu_valo'))['total'] or 0

        # Recebimentos parciais a partir de Baretitulos, respeitando filtros principais
        parciais_qs = Baretitulos.objects.using(self.db_alias).filter(bare_topa='P')
        if self.empresa_id:
            parciais_qs = parciais_qs.filter(bare_empr=self.empresa_id)
        if self.filial_id:
            parciais_qs = parciais_qs.filter(bare_fili=self.filial_id)
        if preserved['titu_clie']:
            parciais_qs = parciais_qs.filter(bare_clie=preserved['titu_clie'])
        if preserved['venc_ini']:
            parciais_qs = parciais_qs.filter(bare_venc__gte=preserved['venc_ini'])
        if preserved['venc_fim']:
            parciais_qs = parciais_qs.filter(bare_venc__lte=preserved['venc_fim'])
        if preserved['titu_parc']:
            parciais_qs = parciais_qs.filter(bare_parc=preserved['titu_parc'])

        agg_parciais = parciais_qs.aggregate(
            total_valo_pago=Sum('bare_valo_pago'),
            total_sub_tota=Sum('bare_sub_tota')
        )
        total_recebido_parcial = (agg_parciais['total_valo_pago'] or agg_parciais['total_sub_tota'] or 0)

        total_recebido = (total_quitado or 0) + (total_recebido_parcial or 0)
        total_em_aberto = max((total_geral or 0) - (total_recebido or 0), 0)
        percent_recebido = (float(total_recebido) / float(total_geral) * 100) if total_geral else 0
        percent_a_receber = 100 - percent_recebido if total_geral else 0

        context.update({
            'slug': self.slug,
            'empresa_id': self.empresa_id,
            'filial_id': self.filial_id,
            'preserved_query': urlencode(preserved_qs),
            'filters': preserved,
            'total_recebido': total_recebido,
            'total_em_aberto': total_em_aberto,
            'percent_recebido': percent_recebido,
            'percent_a_receber': percent_a_receber,
        })
        return context

def autocomplete_clientes(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id')
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    qs = Entidades.objects.using(banco).filter(enti_empr=str(empresa_id))
    if term:
        if term.isdigit():
            qs = qs.filter(enti_clie__icontains=term)
        else:
            qs = qs.filter(enti_nome__icontains=term)
    qs = qs.order_by('enti_nome')[:20]
    data = [{'id': str(obj.enti_clie), 'text': f"{obj.enti_clie} - {obj.enti_nome}"} for obj in qs]
    return JsonResponse({'results': data})
