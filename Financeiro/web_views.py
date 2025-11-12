from django.views.generic import TemplateView
from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.utils.http import urlencode

from core.utils import get_licenca_db_config
from contas_a_receber.models import Baretitulos
from contas_a_pagar.models import Bapatitulos


class DBAndSlugMixin:
    slug_url_kwarg = 'slug'

    def dispatch(self, request, *args, **kwargs):
        db_alias = get_licenca_db_config(request)
        setattr(request, 'db_alias', db_alias)
        self.db_alias = db_alias

        self.empresa_id = (
            request.session.get('empresa_id')
            or request.headers.get('X-Empresa')
        )
        self.filial_id = (
            request.session.get('filial_id')
            or request.headers.get('X-Filial')
        )
        self.slug = kwargs.get(self.slug_url_kwarg)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = getattr(self, 'slug', None)
        context['current_year'] = timezone.now().year
        return context


class FluxoCaixaView(DBAndSlugMixin, TemplateView):
    template_name = 'Financeiro/fluxo_caixa.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Parâmetros de filtro
        data_ini = self.request.GET.get('data_ini')
        data_fim = self.request.GET.get('data_fim')
        saldo_inicial = self.request.GET.get('saldo_inicial')

        # Defaults para o mês corrente
        today = timezone.now().date()
        default_ini = today.replace(day=1)
        default_fim = today

        # Preservar filtros
        preserved = {
            'data_ini': data_ini or default_ini.isoformat(),
            'data_fim': data_fim or default_fim.isoformat(),
            'saldo_inicial': saldo_inicial or '0.00',
        }
        preserved_qs = {k: v for k, v in preserved.items() if v}

        # Query de recebimentos e pagamentos dentro do período
        rec_qs = Baretitulos.objects.using(self.db_alias)
        pag_qs = Bapatitulos.objects.using(self.db_alias)

        if self.empresa_id:
            rec_qs = rec_qs.filter(bare_empr=self.empresa_id)
            pag_qs = pag_qs.filter(bapa_empr=self.empresa_id)
        if self.filial_id:
            rec_qs = rec_qs.filter(bare_fili=self.filial_id)
            pag_qs = pag_qs.filter(bapa_fili=self.filial_id)

        # Datas
        rec_qs = rec_qs.filter(bare_dpag__range=(preserved['data_ini'], preserved['data_fim']))
        pag_qs = pag_qs.filter(bapa_dpag__range=(preserved['data_ini'], preserved['data_fim']))

        # Totais
        total_recebimentos = rec_qs.aggregate(
            total=Sum('bare_sub_tota')
        )['total'] or 0

        total_pagamentos = pag_qs.aggregate(
            total=Sum('bapa_sub_tota')
        )['total'] or 0

        try:
            saldo_inicial_val = float(preserved['saldo_inicial'])
        except Exception:
            saldo_inicial_val = 0.0

        saldo_final = (saldo_inicial_val or 0) + float(total_recebimentos) - float(total_pagamentos)

        # Agregações mensais
        rec_mensal = rec_qs.annotate(mes=TruncMonth('bare_dpag')).values('mes').annotate(valor=Sum('bare_sub_tota'))
        pag_mensal = pag_qs.annotate(mes=TruncMonth('bapa_dpag')).values('mes').annotate(valor=Sum('bapa_sub_tota'))

        # Mesclar por mês
        mensal_map = {}
        for r in rec_mensal:
            mensal_map[r['mes']] = {'mes': r['mes'], 'recebimentos': float(r['valor'] or 0), 'pagamentos': 0.0}
        for p in pag_mensal:
            entry = mensal_map.get(p['mes'], {'mes': p['mes'], 'recebimentos': 0.0, 'pagamentos': 0.0})
            entry['pagamentos'] = float(p['valor'] or 0)
            mensal_map[p['mes']] = entry

        movimentos_mensais = []
        for _, m in sorted(mensal_map.items(), key=lambda x: x[0]):
            m['saldo'] = m['recebimentos'] - m['pagamentos']
            movimentos_mensais.append(m)

        context.update({
            'slug': self.slug,
            'empresa_id': self.empresa_id,
            'filial_id': self.filial_id,
            'preserved_query': urlencode(preserved_qs),
            'filters': preserved,
            'total_recebimentos': total_recebimentos,
            'total_pagamentos': total_pagamentos,
            'saldo_inicial': saldo_inicial_val,
            'saldo_final': saldo_final,
            'movimentos_mensais': movimentos_mensais,
        })
        return context