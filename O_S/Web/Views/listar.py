from django.views.generic import ListView
from urllib.parse import quote_plus
from django.db.models import Subquery, OuterRef, BigIntegerField, Sum, Count
from django.db.models.functions import Cast
from core.utils import get_licenca_db_config
from ...models import Os

STATUS_ORDENS = [
    {'value': 0, 'label': 'Aberto'},
    {'value': 1, 'label': 'Orçamento Gerado'},
    {'value': 2, 'label': 'Aguardando Liberação'},
    {'value': 3, 'label': 'Liberada'},
    {'value': 4, 'label': 'Finalizada'},
    {'value': 5, 'label': 'Reprovada'},
    {'value': 20, 'label': 'Faturada Parcial'},
    {'value': 21, 'label': 'Atrasada'},
]

MAP_CORES = {
    0: '#FFC107',
    1: '#FF9800',
    2: '#007BFF',
    3: '#28A745',
    4: '#6C757D',
    5: '#DC3545',
    20: '#20C997',
    21: '#DC3545',
}

class OsListView(ListView):
    model = Os
    template_name = 'Os/os_listar.html'
    context_object_name = 'os'
    paginate_by = 20

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        from Entidades.models import Entidades
        qs = Os.objects.using(banco).filter(
            os_empr=self.request.session.get('empresa_id', 1),
            os_fili=self.request.session.get('filiacao_id', 1),
        )
        cliente_param = (self.request.GET.get('cliente') or '').strip()
        vendedor_param = (self.request.GET.get('vendedor') or '').strip()
        status = self.request.GET.get('status')
        if cliente_param:
            if cliente_param.isdigit():
                qs = qs.filter(os_clie__icontains=cliente_param)
            else:
                entidades_ids = list(
                    Entidades.objects.using(banco)
                    .filter(enti_nome__icontains=cliente_param)
                    .values_list('enti_clie', flat=True)[:200]
                )
                if entidades_ids:
                    qs = qs.filter(os_clie__in=entidades_ids)
                else:
                    qs = qs.none()
        if vendedor_param:
            if vendedor_param.isdigit():
                qs = qs.filter(os_resp__icontains=vendedor_param)
            else:
                vendedores_ids = list(
                    Entidades.objects.using(banco)
                    .filter(enti_nome__icontains=vendedor_param)
                    .values_list('enti_clie', flat=True)[:200]
                )
                if vendedores_ids:
                    qs = qs.filter(os_resp__in=vendedores_ids)
                else:
                    qs = qs.none()
        if status not in (None, '', 'todos'):
            try:
                status_int = int(status)
                qs = qs.filter(os_stat_os=status_int)
            except (ValueError, TypeError):
                pass
        cliente_nome_subq = (
            Entidades.objects.using(banco)
            .filter(enti_clie=Cast(OuterRef('os_clie'), BigIntegerField()))
            .values('enti_nome')[:1]
        )
        vendedor_nome_subq = (
            Entidades.objects.using(banco)
            .filter(enti_clie=Cast(OuterRef('os_resp'), BigIntegerField()))
            .values('enti_nome')[:1]
        )
        qs = qs.annotate(
            cliente_nome=Subquery(cliente_nome_subq),
            vendedor_nome=Subquery(vendedor_nome_subq)
        ).order_by('-os_data_aber', '-os_os')
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')
        banco = get_licenca_db_config(self.request) or 'default'
        from Entidades.models import Entidades
        qs_total = Os.objects.using(banco).filter(
            os_empr=self.request.session.get('empresa_id', 1),
            os_fili=self.request.session.get('filiacao_id', 1),
        )
        cliente_param = (self.request.GET.get('cliente') or '').strip()
        vendedor_param = (self.request.GET.get('vendedor') or '').strip()
        status = self.request.GET.get('status')
        if cliente_param:
            if cliente_param.isdigit():
                qs_total = qs_total.filter(os_clie__icontains=cliente_param)
            else:
                entidades_ids = list(
                    Entidades.objects.using(banco)
                    .filter(enti_nome__icontains=cliente_param)
                    .values_list('enti_clie', flat=True)[:200]
                )
                if entidades_ids:
                    qs_total = qs_total.filter(os_clie__in=entidades_ids)
                else:
                    qs_total = qs_total.none()
        if vendedor_param:
            if vendedor_param.isdigit():
                qs_total = qs_total.filter(os_resp__icontains=vendedor_param)
            else:
                vendedores_ids = list(
                    Entidades.objects.using(banco)
                    .filter(enti_nome__icontains=vendedor_param)
                    .values_list('enti_clie', flat=True)[:200]
                )
                if vendedores_ids:
                    qs_total = qs_total.filter(os_resp__in=vendedores_ids)
                else:
                    qs_total = qs_total.none()
        if status not in (None, '', 'todos'):
            try:
                status_int = int(status)
                qs_total = qs_total.filter(os_stat_os=status_int)
            except (ValueError, TypeError):
                pass
        context['total_registros'] = qs_total.count()
        context['total_valor'] = qs_total.aggregate(Sum('os_tota'))['os_tota__sum'] or 0

        # Cards por status
        status_labels = {s['value']: s['label'] for s in STATUS_ORDENS}
        agg = list(
            qs_total.values('os_stat_os').annotate(qtd=Count('os_os'), valor=Sum('os_tota'))
        )
        by_status = {int(a['os_stat_os'] or 0): a for a in agg}
        cards = []
        for s in STATUS_ORDENS:
            val = int(s['value'])
            a = by_status.get(val, {'qtd': 0, 'valor': 0})
            cards.append({
                'status': val,
                'label': s['label'],
                'color': MAP_CORES.get(val, '#6C757D'),
                'qtd': int(a.get('qtd') or 0),
                'valor': float(a.get('valor') or 0),
            })
        context['cards_por_status'] = cards
        context['status_ordens'] = STATUS_ORDENS
        params = []
        for key in ['cliente', 'vendedor', 'status']:
            val = (self.request.GET.get(key) or '').strip()
            if val:
                params.append(f"{quote_plus(key)}={quote_plus(val)}")
        context['extra_query'] = ("&" + "&".join(params)) if params else ""
        return context