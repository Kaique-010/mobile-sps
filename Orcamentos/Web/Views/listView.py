from django.views.generic import ListView
from urllib.parse import quote_plus
from django.db.models import Subquery, OuterRef, BigIntegerField, Sum, Count
from django.db.models.functions import Cast
from core.utils import get_licenca_db_config
from ...models import Orcamentos

class OrcamentosListView(ListView):
    model = Orcamentos
    template_name = 'Orcamentos/orcamentos_listar.html'
    context_object_name = 'orcamentos'
    paginate_by = 50

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        from Entidades.models import Entidades
        qs = Orcamentos.objects.using(banco).filter(
            pedi_empr=self.request.session.get('empresa_id', 1),
            pedi_fili=self.request.session.get('filial_id', 1),
        )
        cliente_param = (self.request.GET.get('cliente') or '').strip()
        vendedor_param = (self.request.GET.get('vendedor') or '').strip()
        status = self.request.GET.get('status')
        if cliente_param:
            if cliente_param.isdigit():
                qs = qs.filter(pedi_forn__icontains=cliente_param)
            else:
                entidades_ids = list(
                    Entidades.objects.using(banco)
                    .filter(enti_nome__icontains=cliente_param)
                    .values_list('enti_clie', flat=True)[:200]
                )
                if entidades_ids:
                    qs = qs.filter(pedi_forn__in=entidades_ids)
                else:
                    qs = qs.none()
        if vendedor_param:
            if vendedor_param.isdigit():
                qs = qs.filter(pedi_vend__icontains=vendedor_param)
            else:
                vendedores_ids = list(
                    Entidades.objects.using(banco)
                    .filter(enti_nome__icontains=vendedor_param)
                    .values_list('enti_clie', flat=True)[:200]
                )
                if vendedores_ids:
                    qs = qs.filter(pedi_vend__in=vendedores_ids)
                else:
                    qs = qs.none()
        if status not in (None, '', 'todos'):
            qs = qs.filter(pedi_stat=status)
        cliente_nome_subq = (
            Entidades.objects.using(banco)
            .filter(enti_clie=Cast(OuterRef('pedi_forn'), BigIntegerField()))
            .values('enti_nome')[:1]
        )
        vendedor_nome_subq = (
            Entidades.objects.using(banco)
            .filter(enti_clie=Cast(OuterRef('pedi_vend'), BigIntegerField()))
            .values('enti_nome')[:1]
        )
        qs = qs.annotate(
            cliente_nome=Subquery(cliente_nome_subq),
            vendedor_nome=Subquery(vendedor_nome_subq)
        ).order_by('-pedi_data', '-pedi_nume')
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')
        banco = get_licenca_db_config(self.request) or 'default'
        from Entidades.models import Entidades
        qs_total = Orcamentos.objects.using(banco).filter(
            pedi_empr=self.request.session.get('empresa_id', 1),
            pedi_fili=self.request.session.get('filial_id', 1),
        )
        cliente_param = (self.request.GET.get('cliente') or '').strip()
        vendedor_param = (self.request.GET.get('vendedor') or '').strip()
        status = self.request.GET.get('status')
        if cliente_param:
            if cliente_param.isdigit():
                qs_total = qs_total.filter(pedi_forn__icontains=cliente_param)
            else:
                entidades_ids = list(
                    Entidades.objects.using(banco)
                    .filter(enti_nome__icontains=cliente_param)
                    .values_list('enti_clie', flat=True)[:200]
                )
                if entidades_ids:
                    qs_total = qs_total.filter(pedi_forn__in=entidades_ids)
                else:
                    qs_total = qs_total.none()
        if vendedor_param:
            if vendedor_param.isdigit():
                qs_total = qs_total.filter(pedi_vend__icontains=vendedor_param)
            else:
                vendedores_ids = list(
                    Entidades.objects.using(banco)
                    .filter(enti_nome__icontains=vendedor_param)
                    .values_list('enti_clie', flat=True)[:200]
                )
                if vendedores_ids:
                    qs_total = qs_total.filter(pedi_vend__in=vendedores_ids)
                else:
                    qs_total = qs_total.none()
        if status not in (None, '', 'todos'):
            qs_total = qs_total.filter(pedi_stat=status)
        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)
        qs_total = qs_total.filter(pedi_empr=empresa_id, pedi_fili=filial_id)
        context['total_registros'] = qs_total.count()
        context['total_valor'] = qs_total.aggregate(Sum('pedi_tota'))['pedi_tota__sum'] or 0
        distintos_clientes = qs_total.values('pedi_forn').distinct().count()
        context['cards_resumo'] = [
            {'label': 'Total de Orçamentos', 'qtd': context['total_registros'], 'valor': context['total_valor'], 'color': '#4a6cf7'},
            {'label': 'Clientes Distintos', 'qtd': distintos_clientes, 'valor': None, 'color': '#6ec1e4'},
        ]
        STATUS_ORC = [
            {'value': '0', 'label': 'Aberto'},
            {'value': '1', 'label': 'Processando'},
            {'value': '2', 'label': 'Exportado'},
            {'value': '3', 'label': 'Concluído'},
            {'value': '4', 'label': 'Cancelado'},
        ]
        MAP_CORES_ORC = {
            '0': '#FFC107',
            '1': '#0D6EFD',
            '2': '#6610f2',
            '3': '#28A745',
            '4': '#6C757D',
        }
        agg = list(qs_total.values('pedi_stat').annotate(qtd=Count('pedi_nume'), valor=Sum('pedi_tota')))
        by_status = {str(a['pedi_stat']): a for a in agg}
        cards_status = []
        for s in STATUS_ORC:
            k = str(s['value'])
            a = by_status.get(k, {'qtd': 0, 'valor': 0})
            cards_status.append({
                'status': k,
                'label': s['label'],
                'color': MAP_CORES_ORC.get(k, '#6C757D'),
                'qtd': int(a.get('qtd') or 0),
                'valor': float(a.get('valor') or 0),
            })
        context['cards_por_status'] = cards_status
        params = []
        for key in ['cliente', 'vendedor', 'status']:
            val = (self.request.GET.get(key) or '').strip()
            if val:
                params.append(f"{quote_plus(key)}={quote_plus(val)}")
        context['extra_query'] = ("&" + "&".join(params)) if params else ""
        return context