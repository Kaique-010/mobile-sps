from django.views.generic import TemplateView, ListView
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta, date
from .mixin import DBAndSlugMixin
from Entidades.models import Entidades
from contas_a_pagar.models import Titulospagar
from contas_a_receber.models import Titulosreceber
from Pedidos.models import PedidoVenda
from Orcamentos.models import Orcamentos
from logging import getLogger


logger = getLogger(__name__)


def _local_today():
    now = timezone.now()
    if timezone.is_naive(now):
        return now.date()
    return timezone.localtime(now).date()


def _week_range(base):
    start = base - timedelta(days=base.weekday())
    end = start + timedelta(days=6)
    return start, end


def _day_bounds(day):
    start = day
    end = day + timedelta(days=1)
    return start, end


class NotificacoesDashboardView(DBAndSlugMixin, TemplateView):
    template_name = 'Notificacoes/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = _local_today()
        w_start, w_end = _week_range(today)
        d_start, d_end = _day_bounds(today)
        
        fornecedores = dict(
            Entidades.objects.using(self.db_alias)
            .filter(enti_empr=self.empresa_id)
            .values_list('enti_clie', 'enti_nome')
        )
        logger.info(f'fornecedores: {fornecedores}')

        pagar_qs = Titulospagar.objects.using(self.db_alias).filter(titu_empr=self.empresa_id, titu_fili=self.filial_id)
        logger.info(f'pagar_qs: {pagar_qs}')
        receber_qs = Titulosreceber.objects.using(self.db_alias).filter(titu_empr=self.empresa_id, titu_fili=self.filial_id)
        logger.info(f'receber_qs: {receber_qs}')
        orc_qs = Orcamentos.objects.using(self.db_alias).filter(pedi_empr=self.empresa_id, pedi_fili=self.filial_id)
        logger.info(f'orc_qs: {orc_qs}')
        ped_qs = PedidoVenda.objects.using(self.db_alias).filter(pedi_empr=self.empresa_id, pedi_fili=self.filial_id)
        logger.info(f'ped_qs: {ped_qs}')

        def _to_row(obj, tipo):
            forn_id = getattr(obj, 'titu_forn', None)
            return {
                'tipo': tipo,
                'titu_titu': getattr(obj, 'titu_titu', ''),
                'titu_parc': getattr(obj, 'titu_parc', ''),
                'titu_valo': getattr(obj, 'titu_valo', ''),
                'titu_forn': forn_id,
                'forncedor_nome': fornecedores.get(forn_id, ''),
                'titu_venc': getattr(obj, 'titu_venc', ''),
                'titu_aber': getattr(obj, 'titu_aber', ''),
            }
        receber_rows = [_to_row(o, 'Receber') for o in receber_qs.filter(titu_emis__gte=d_start, titu_emis__lt=d_end)[:10]]
        pagar_rows = [_to_row(o, 'Pagar') for o in pagar_qs.filter(titu_emis__gte=d_start, titu_emis__lt=d_end)[:10]]
        titulos_criados_hoje = receber_rows + pagar_rows
        w_end_inclusive = w_end + timedelta(days=1)
        pagar_hoje = pagar_qs.filter(titu_venc__gte=d_start, titu_venc__lt=d_end)
        pagar_semana = pagar_qs.filter(titu_venc__gte=w_start, titu_venc__lt=w_end_inclusive)
        receber_hoje = receber_qs.filter(titu_venc__gte=d_start, titu_venc__lt=d_end)
        receber_semana = receber_qs.filter(titu_venc__gte=w_start, titu_venc__lt=w_end_inclusive)
        orcamentos_hoje = orc_qs.filter(pedi_data__gte=d_start, pedi_data__lt=d_end)
        pedidos_hoje = ped_qs.filter(pedi_data__gte=d_start, pedi_data__lt=d_end)

        ctx.update({
            'today': today,
            'pagar_hoje_count': pagar_hoje.count(),
            'pagar_semana_count': pagar_semana.count(),
            'receber_hoje_count': receber_hoje.count(),
            'receber_semana_count': receber_semana.count(),
            'titulos_criados_hoje': titulos_criados_hoje,
            'orcamentos_hoje_count': orcamentos_hoje.count(),
            'pedidos_hoje_count': pedidos_hoje.count(),
        })
        return ctx


class TitulosCriadosHojeListView(DBAndSlugMixin, ListView):
    template_name = 'Notificacoes/list_titulos.html'
    paginate_by = 50

    def get_queryset(self):
        today = _local_today()
        tipo = (self.request.GET.get('tipo') or '').lower()
        d_start, d_end = _day_bounds(today)
        pagar_qs = Titulospagar.objects.using(self.db_alias).filter(titu_empr=self.empresa_id, titu_fili=self.filial_id, titu_emis__gte=d_start, titu_emis__lt=d_end).order_by('titu_venc', 'titu_titu')
        receber_qs = Titulosreceber.objects.using(self.db_alias).filter(titu_empr=self.empresa_id, titu_fili=self.filial_id, titu_emis__gte=d_start, titu_emis__lt=d_end).order_by('titu_venc', 'titu_titu')

        fornecedores = dict(
            Entidades.objects.using(self.db_alias)
            .filter(enti_empr=self.empresa_id)
            .values_list('enti_clie', 'enti_nome')
        )

        def _to_row(obj, tipo_label):
            forn_id = getattr(obj, 'titu_forn', None)
            return {
                'tipo': tipo_label,
                'titu_titu': getattr(obj, 'titu_titu', ''),
                'titu_parc': getattr(obj, 'titu_parc', ''),
                'titu_valo': getattr(obj, 'titu_valo', ''),
                'titu_forn': forn_id,
                'forncedor_nome': fornecedores.get(forn_id, ''),
                'titu_venc': getattr(obj, 'titu_venc', ''),
                'titu_aber': getattr(obj, 'titu_aber', ''),
            }
        if tipo == 'pagar':
            return [_to_row(o, 'Pagar') for o in pagar_qs]
        if tipo == 'receber':
            return [_to_row(o, 'Receber') for o in receber_qs]
        return ([_to_row(o, 'Pagar') for o in pagar_qs] + [_to_row(o, 'Receber') for o in receber_qs])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'today': _local_today(), 'tipo': (self.request.GET.get('tipo') or '').lower(), 'slug': self.slug})
        return ctx


class TitulosAPagarListView(DBAndSlugMixin, ListView):
    model = Titulospagar
    template_name = 'Notificacoes/list_pagar.html'
    paginate_by = 50

    def get_queryset(self):
        today = _local_today()
        period = (self.request.GET.get('period') or 'hoje').lower()
        qs = Titulospagar.objects.using(self.db_alias).filter(titu_empr=self.empresa_id, titu_fili=self.filial_id)
        qs = qs.filter(
            (Q(titu_emis__isnull=True) | Q(titu_emis__gte=date(1900,1,1))),
            (Q(titu_venc__isnull=True) | Q(titu_venc__gte=date(1900,1,1))),
        )
        if period == 'semana':
            w_start, w_end = _week_range(today)
            qs = qs.filter(titu_venc__gte=w_start, titu_venc__lt=w_end + timedelta(days=1))
        else:
            d_start, d_end = _day_bounds(today)
            qs = qs.filter(titu_venc__gte=d_start, titu_venc__lt=d_end)
        status = self.request.GET.get('status')
        if status == 'aberto':
            qs = qs.filter(titu_aber='A')
        if status == 'quitado':
            qs = qs.filter(titu_aber='T')
        qs = qs.order_by('titu_forn', 'titu_venc', 'titu_titu').only('titu_titu','titu_parc','titu_venc','titu_aber','titu_forn','titu_valo')
        fornecedores = dict(
            Entidades.objects.using(self.db_alias)
            .filter(enti_empr=self.empresa_id)
            .values_list('enti_clie', 'enti_nome')
        )
        def _to_row(o):
            return {
                'titu_titu': getattr(o, 'titu_titu', ''),
                'titu_forn': getattr(o, 'titu_forn', ''),
                'fornecedor_nome': fornecedores.get(getattr(o, 'titu_forn', ''), ''),
                'titu_valo': getattr(o, 'titu_valo', ''),
                'titu_parc': getattr(o, 'titu_parc', ''),
                'titu_venc': getattr(o, 'titu_venc', ''),
                'titu_aber': getattr(o, 'titu_aber', ''),
            }
        return [
            _to_row(o) for o in qs
        ]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        objs = ctx.get('object_list') or getattr(self, 'object_list', [])
        try:
            total_count = len(objs)
            total_sum = sum(float((o.get('titu_valo') if isinstance(o, dict) else getattr(o, 'titu_valo', 0)) or 0) for o in objs)
        except Exception:
            total_count, total_sum = 0, 0.0
        ctx.update({'today': _local_today(), 'period': (self.request.GET.get('period') or 'hoje').lower(), 'slug': self.slug, 'total_count': total_count, 'total_sum': total_sum})
        return ctx


class TitulosAReceberListView(DBAndSlugMixin, ListView):
    model = Titulosreceber
    template_name = 'Notificacoes/list_receber.html'
    paginate_by = 50

    def get_queryset(self):
        today = _local_today()
        period = (self.request.GET.get('period') or 'hoje').lower()
        qs = Titulosreceber.objects.using(self.db_alias).filter(titu_empr=self.empresa_id, titu_fili=self.filial_id)
        qs = qs.filter(
            (Q(titu_emis__isnull=True) | Q(titu_emis__gte=date(1900,1,1))),
            (Q(titu_venc__isnull=True) | Q(titu_venc__gte=date(1900,1,1))),
        )
        if period == 'semana':
            w_start, w_end = _week_range(today)
            qs = qs.filter(titu_venc__gte=w_start, titu_venc__lt=w_end + timedelta(days=1))
        else:
            d_start, d_end = _day_bounds(today)
            qs = qs.filter(titu_venc__gte=d_start, titu_venc__lt=d_end)
        status = self.request.GET.get('status')
        if status == 'aberto':
            qs = qs.filter(titu_aber='A')
        if status == 'quitado':
            qs = qs.filter(titu_aber='T')
        qs = qs.order_by('titu_clie', 'titu_venc', 'titu_titu').only('titu_titu','titu_parc','titu_venc','titu_aber','titu_clie','titu_valo')
        clientes = dict(
            Entidades.objects.using(self.db_alias)
            .filter(enti_empr=self.empresa_id)
            .values_list('enti_clie', 'enti_nome')
        )
        def _to_row(o):
            return {
                'titu_titu': getattr(o, 'titu_titu', ''),
                'titu_clie': getattr(o, 'titu_clie', ''),
                'cliente_nome': clientes.get(getattr(o, 'titu_clie', ''), ''),
                'titu_valo': getattr(o, 'titu_valo', ''),
                'titu_parc': getattr(o, 'titu_parc', ''),
                'titu_venc': getattr(o, 'titu_venc', ''),
                'titu_aber': getattr(o, 'titu_aber', ''),
            }
        return [
            _to_row(o) for o in qs
        ]


    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        objs = ctx.get('object_list') or getattr(self, 'object_list', [])
        try:
            total_count = len(objs)
            total_sum = sum(float((o.get('titu_valo') if isinstance(o, dict) else getattr(o, 'titu_valo', 0)) or 0) for o in objs)
        except Exception:
            total_count, total_sum = 0, 0.0
        ctx.update({'today': _local_today(), 'period': (self.request.GET.get('period') or 'hoje').lower(), 'slug': self.slug, 'total_count': total_count, 'total_sum': total_sum})
        return ctx


class OrcamentosHojeListView(DBAndSlugMixin, ListView):
    model = Orcamentos
    template_name = 'Notificacoes/list_orcamentos.html'
    paginate_by = 50

    def get_queryset(self):
        today = _local_today()
        qs = Orcamentos.objects.using(self.db_alias).filter(pedi_empr=self.empresa_id, pedi_fili=self.filial_id, pedi_data=today)
        return qs.order_by('-pedi_nume')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'today': _local_today(), 'slug': self.slug})
        return ctx


class PedidosHojeListView(DBAndSlugMixin, ListView):
    model = PedidoVenda
    template_name = 'Notificacoes/list_pedidos.html'
    paginate_by = 50

    def get_queryset(self):
        today = _local_today()
        qs = PedidoVenda.objects.using(self.db_alias).filter(pedi_empr=self.empresa_id, pedi_fili=self.filial_id, pedi_data=today)
        return qs.order_by('-pedi_nume')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'today': _local_today(), 'slug': self.slug})
        return ctx
