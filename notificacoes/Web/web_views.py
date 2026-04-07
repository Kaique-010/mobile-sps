from django.views.generic import TemplateView, ListView
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta, date
from .mixin import DBAndSlugMixin
from Entidades.models import Entidades
from contas_a_pagar.models import Titulospagar
from contas_a_receber.models import Titulosreceber
from contas_a_pagar.models import Bapatitulos
from contas_a_receber.models import Baretitulos
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

        pagar_all_qs = Titulospagar.objects.using(self.db_alias).filter(titu_empr=self.empresa_id, titu_fili=self.filial_id)
        logger.info(f'pagar_all_qs: {pagar_all_qs}')
        receber_all_qs = Titulosreceber.objects.using(self.db_alias).filter(titu_empr=self.empresa_id, titu_fili=self.filial_id)
        logger.info(f'receber_all_qs: {receber_all_qs}')
        
        
        pagas_qs = Bapatitulos.objects.using(self.db_alias).filter(bapa_empr=self.empresa_id, bapa_fili=self.filial_id, bapa_dpag__gte=d_start, bapa_dpag__lt=d_end)
        logger.info(f'pagas_qs: {pagas_qs}')
        recebidas_qs = Baretitulos.objects.using(self.db_alias).filter(bare_empr=self.empresa_id, bare_fili=self.filial_id, bare_dpag__gte=d_start, bare_dpag__lt=d_end)
        logger.info(f'recebidas_qs: {recebidas_qs}')
        
        
        orc_qs = Orcamentos.objects.using(self.db_alias).filter(pedi_empr=self.empresa_id, pedi_fili=self.filial_id, pedi_data__gte=d_start, pedi_data__lt=d_end)
        logger.info(f'orc_qs: {orc_qs}')
        ped_qs = PedidoVenda.objects.using(self.db_alias).filter(pedi_empr=self.empresa_id, pedi_fili=self.filial_id)
        logger.info(f'ped_qs: {ped_qs}')

        def _to_row(obj, tipo):
            if tipo == 'Paga':
                titu = getattr(obj, 'bapa_titu', '') or getattr(obj, 'titu_titu', '')
                parc = getattr(obj, 'bapa_parc', '') or getattr(obj, 'titu_parc', '')
                valo = getattr(obj, 'bapa_valo_pago', '') or getattr(obj, 'bapa_valo', '') or getattr(obj, 'titu_valo', '')
                forn_id = getattr(obj, 'bapa_forn', None) or getattr(obj, 'titu_forn', None)
                venc = getattr(obj, 'bapa_dpag', '') or getattr(obj, 'titu_venc', '')
                aber = 'T'
            elif tipo == 'Recebida':
                titu = getattr(obj, 'bare_titu', '') or getattr(obj, 'titu_titu', '')
                parc = getattr(obj, 'bare_parc', '') or getattr(obj, 'titu_parc', '')
                valo = getattr(obj, 'bare_valo_pago', '') or getattr(obj, 'bare_valo', '') or getattr(obj, 'titu_valo', '')
                forn_id = getattr(obj, 'bare_clie', None) or getattr(obj, 'titu_clie', None) or getattr(obj, 'titu_forn', None)
                venc = getattr(obj, 'bare_dpag', '') or getattr(obj, 'titu_venc', '')
                aber = 'T'
            else:
                titu = getattr(obj, 'titu_titu', '')
                parc = getattr(obj, 'titu_parc', '')
                valo = getattr(obj, 'titu_valo', '')
                forn_id = getattr(obj, 'titu_forn', None) or getattr(obj, 'titu_clie', None)
                venc = getattr(obj, 'titu_venc', '')
                aber = getattr(obj, 'titu_aber', '')
            return {
                'tipo': tipo,
                'titu_titu': titu,
                'titu_parc': parc,
                'titu_valo': valo,
                'titu_forn': forn_id,
                'forncedor_nome': fornecedores.get(forn_id, ''),
                'titu_venc': venc,
                'titu_aber': aber,
                
            }
        receber_rows = [_to_row(o, 'Receber') for o in receber_all_qs.filter(titu_emis__gte=d_start, titu_emis__lt=d_end)[:10]]
        pagar_rows = [_to_row(o, 'Pagar') for o in pagar_all_qs.filter(titu_emis__gte=d_start, titu_emis__lt=d_end)[:10]]
        pagas_rows = [_to_row(o, 'Paga') for o in pagas_qs.filter(bapa_dpag__gte=d_start, bapa_dpag__lt=d_end)[:10]]
        recebidas_rows = [_to_row(o, 'Recebida') for o in recebidas_qs.filter(bare_dpag__gte=d_start, bare_dpag__lt=d_end)[:10]]
        titulos_criados_hoje = receber_rows + pagar_rows + pagas_rows + recebidas_rows
        w_end_inclusive = w_end + timedelta(days=1)
        pagar_hoje = pagar_all_qs.filter(titu_venc__gte=d_start, titu_venc__lt=d_end)
        pagar_semana = pagar_all_qs.filter(titu_venc__gte=w_start, titu_venc__lt=w_end_inclusive)
        receber_hoje = receber_all_qs.filter(titu_venc__gte=d_start, titu_venc__lt=d_end)
        receber_semana = receber_all_qs.filter(titu_venc__gte=w_start, titu_venc__lt=w_end_inclusive)
        pagas_hoje_count = Bapatitulos.objects.using(self.db_alias).filter(bapa_empr=self.empresa_id, bapa_fili=self.filial_id, bapa_dpag__gte=d_start, bapa_dpag__lt=d_end).count()
        pagas_semana_count = Bapatitulos.objects.using(self.db_alias).filter(bapa_empr=self.empresa_id, bapa_fili=self.filial_id, bapa_dpag__gte=w_start, bapa_dpag__lt=w_end_inclusive).count()
        recebidas_hoje_count = Baretitulos.objects.using(self.db_alias).filter(bare_empr=self.empresa_id, bare_fili=self.filial_id, bare_dpag__gte=d_start, bare_dpag__lt=d_end).count()
        recebidas_semana_count = Baretitulos.objects.using(self.db_alias).filter(bare_empr=self.empresa_id, bare_fili=self.filial_id, bare_dpag__gte=w_start, bare_dpag__lt=w_end_inclusive).count()
        orcamentos_hoje = orc_qs.filter(pedi_data__gte=d_start, pedi_data__lt=d_end)
        pedidos_hoje = ped_qs.filter(pedi_data__gte=d_start, pedi_data__lt=d_end)

        ctx.update({
            'today': today,
            'pagar_hoje_count': pagar_hoje.count(),
            'pagar_semana_count': pagar_semana.count(),
            'receber_hoje_count': receber_hoje.count(),
            'receber_semana_count': receber_semana.count(),
            'pagas_hoje_count': pagas_hoje_count,
            'pagas_semana_count': pagas_semana_count,
            'recebidas_hoje_count': recebidas_hoje_count,
            'recebidas_semana_count': recebidas_semana_count,
            'titulos_criados_hoje': titulos_criados_hoje,
            'pagas_rows': pagas_rows,
            'recebidas_rows': recebidas_rows,
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
        pagas_qs = Bapatitulos.objects.using(self.db_alias).filter(bapa_empr=self.empresa_id, bapa_fili=self.filial_id, bapa_dpag__gte=d_start, bapa_dpag__lt=d_end).order_by('bapa_dpag', 'bapa_titu')
        recebidas_qs = Baretitulos.objects.using(self.db_alias).filter(bare_empr=self.empresa_id, bare_fili=self.filial_id, bare_dpag__gte=d_start, bare_dpag__lt=d_end).order_by('bare_dpag', 'bare_titu')

        fornecedores = dict(
            Entidades.objects.using(self.db_alias)
            .filter(enti_empr=self.empresa_id)
            .values_list('enti_clie', 'enti_nome')
        )

        def _to_row(obj, tipo_label):
            forn_id = getattr(obj, 'titu_forn', None) or getattr(obj, 'bapa_forn', None) or getattr(obj, 'bare_clie', None)
            return {
                'tipo': tipo_label,
                'titu_titu': getattr(obj, 'titu_titu', '') or getattr(obj, 'bapa_titu', '') or getattr(obj, 'bare_titu', ''),
                'titu_parc': getattr(obj, 'titu_parc', '') or getattr(obj, 'bapa_parc', '') or getattr(obj, 'bare_parc', ''),
                'titu_valo': getattr(obj, 'titu_valo', '') or getattr(obj, 'bapa_valo', '') or getattr(obj, 'bare_valo', ''),
                'titu_forn': forn_id,
                'forncedor_nome': fornecedores.get(forn_id, ''),
                'titu_venc': getattr(obj, 'titu_venc', '') or getattr(obj, 'bapa_dpag', '') or getattr(obj, 'bare_dpag', ''),
                'titu_aber': getattr(obj, 'titu_aber', '') or 'T' if tipo_label in ['Paga','Recebida'] else getattr(obj, 'titu_aber', ''),
            }
        if tipo == 'pagar':
            return [_to_row(o, 'Pagar') for o in pagar_qs]
        if tipo == 'receber':
            return [_to_row(o, 'Receber') for o in receber_qs]
        if tipo == 'paga':
            return [_to_row(o, 'Paga') for o in pagas_qs]
        if tipo == 'recebida':
            return [_to_row(o, 'Recebida') for o in recebidas_qs]
        return ([_to_row(o, 'Pagar') for o in pagar_qs] + [_to_row(o, 'Receber') for o in receber_qs] + [_to_row(o, 'Paga') for o in pagas_qs] + [_to_row(o, 'Recebida') for o in recebidas_qs])

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
        status = self.request.GET.get('status')
        if status == 'quitado':
            w_start, w_end = _week_range(today)
            d_start, d_end = _day_bounds(today)
            w_end_inclusive = w_end + timedelta(days=1)
            qs = Bapatitulos.objects.using(self.db_alias).filter(bapa_empr=self.empresa_id, bapa_fili=self.filial_id)
            if period == 'semana':
                qs = qs.filter(bapa_dpag__gte=w_start, bapa_dpag__lt=w_end_inclusive)
            else:
                qs = qs.filter(bapa_dpag__gte=d_start, bapa_dpag__lt=d_end)
            qs = qs.order_by('bapa_dpag', 'bapa_titu')
        else:
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
            if status == 'aberto':
                qs = qs.filter(titu_aber='A')
            qs = qs.order_by('titu_forn', 'titu_venc', 'titu_titu').only('titu_titu','titu_parc','titu_venc','titu_aber','titu_forn','titu_valo')
        fornecedores = dict(
            Entidades.objects.using(self.db_alias)
            .filter(enti_empr=self.empresa_id)
            .values_list('enti_clie', 'enti_nome')
        )
        def _to_row(o):
            forn = getattr(o, 'titu_forn', '') or getattr(o, 'bapa_forn', '')
            valo = getattr(o, 'titu_valo', '') or getattr(o, 'bapa_valo', '')
            parc = getattr(o, 'titu_parc', '') or getattr(o, 'bapa_parc', '')
            venc = getattr(o, 'titu_venc', '') or getattr(o, 'bapa_dpag', '')
            aber = 'T' if status == 'quitado' else getattr(o, 'titu_aber', '')
            return {
                'titu_titu': getattr(o, 'titu_titu', '') or getattr(o, 'bapa_titu', ''),
                'titu_forn': forn,
                'fornecedor_nome': fornecedores.get(forn, ''),
                'titu_valo': valo,
                'titu_parc': parc,
                'titu_venc': venc,
                'titu_aber': aber,
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
        status = self.request.GET.get('status')
        if status == 'quitado':
            w_start, w_end = _week_range(today)
            d_start, d_end = _day_bounds(today)
            w_end_inclusive = w_end + timedelta(days=1)
            qs = Baretitulos.objects.using(self.db_alias).filter(bare_empr=self.empresa_id, bare_fili=self.filial_id)
            if period == 'semana':
                qs = qs.filter(bare_dpag__gte=w_start, bare_dpag__lt=w_end_inclusive)
            else:
                qs = qs.filter(bare_dpag__gte=d_start, bare_dpag__lt=d_end)
            qs = qs.order_by('bare_dpag', 'bare_titu')
        else:
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
            clie = getattr(o, 'titu_clie', '') or getattr(o, 'bare_clie', '')
            valo = getattr(o, 'titu_valo', '') or getattr(o, 'bare_valo', '') or getattr(o, 'bare_valo_pago', '')
            parc = getattr(o, 'titu_parc', '') or getattr(o, 'bare_parc', '')
            venc = getattr(o, 'titu_venc', '') or getattr(o, 'bare_dpag', '')
            aber = 'T' if status == 'quitado' else getattr(o, 'titu_aber', '')
            return {
                'titu_titu': getattr(o, 'titu_titu', '') or getattr(o, 'bare_titu', ''),
                'titu_clie': clie,
                'cliente_nome': clientes.get(clie, ''),
                'titu_valo': valo,
                'titu_parc': parc,
                'titu_venc': venc,
                'titu_aber': aber,
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
