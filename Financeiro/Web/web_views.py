from django.views.generic import TemplateView
from django.views import View
from django.http import JsonResponse
from datetime import date
from calendar import monthrange
from django.utils import timezone
from django.db.models import (
    Sum, Q, OuterRef, Subquery, Value, Func, F, DecimalField
)
from django.db.models.functions import TruncMonth, Coalesce, Greatest
from django.utils.http import urlencode
from django.utils import timezone
from core.utils import get_licenca_db_config
from contas_a_receber.models import Baretitulos, Titulosreceber
from contas_a_pagar.models import Bapatitulos, Titulospagar
from Financeiro.models import Situacoes
from Entidades.models import Entidades


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
        entidade = self.request.GET.get('entidade')
        pagamento = self.request.GET.get('pagamento')




        # Defaults para o mês corrente
        today = timezone.now().date()
        default_ini = today.replace(day=1)
        default_fim = today

        # Preservar filtros
        preserved = {
            'data_ini': data_ini or default_ini.isoformat(),
            'data_fim': data_fim or default_fim.isoformat(),
            'saldo_inicial': saldo_inicial or '0.00',
            'entidade': entidade or '',
            'pagamento': pagamento or '',
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
        
        # Entidade (join manual via tabela entidades)
        if preserved['entidade']:
            ent_qs = Entidades.objects.using(self.db_alias).filter(
                enti_nome__icontains=preserved['entidade'],
            )
            if self.empresa_id:
                ent_qs = ent_qs.filter(enti_empr=self.empresa_id)
            ent_ids = list(ent_qs.values_list('enti_clie', flat=True)[:5000])
            rec_qs = rec_qs.filter(bare_clie__in=ent_ids)
            pag_qs = pag_qs.filter(bapa_forn__in=ent_ids)

        rec_ids = set(rec_qs.values_list('bare_clie', flat=True).distinct())
        pag_ids = set(pag_qs.values_list('bapa_forn', flat=True).distinct())
        ent_ids = {i for i in (rec_ids | pag_ids) if i is not None}

        entidades_qs = Entidades.objects.using(self.db_alias).filter(enti_clie__in=ent_ids)
        if self.empresa_id:
            entidades_qs = entidades_qs.filter(enti_empr=self.empresa_id)
        ent_listas = list(entidades_qs.values('enti_clie', 'enti_nome').order_by('enti_nome')[:5000])

        # Pagamento (forma)
        if preserved['pagamento']:
            rec_qs = rec_qs.filter(bare_form=preserved['pagamento'])
            pag_qs = pag_qs.filter(bapa_form=preserved['pagamento'])

        rec_forms = set(rec_qs.values_list('bare_form', flat=True).distinct())
        pag_forms = set(pag_qs.values_list('bapa_form', flat=True).distinct())
        pag_listas = sorted([f for f in (rec_forms | pag_forms) if f])

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
            'ent_listas': ent_listas,
            'pag_listas': pag_listas,
            'total_pagamentos': total_pagamentos,
            'saldo_inicial': saldo_inicial_val,
            'saldo_final': saldo_final,
            'movimentos_mensais': movimentos_mensais,
        })
        return context


class FluxoCompetenciaView(DBAndSlugMixin, TemplateView):
    template_name = 'Financeiro/fluxo_competencia.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # --- 1. Parâmetros ---
        data_ini = self.request.GET.get('data_ini')
        data_fim = self.request.GET.get('data_fim')
        saldo_inicial = self.request.GET.get('saldo_inicial')
        entidade = self.request.GET.get('entidade')
        pagamento = self.request.GET.get('pagamento')

        today = timezone.now().date()
        default_ini = today.replace(day=1)
        default_fim = today

        preserved = {
            'data_ini': data_ini or default_ini.isoformat(),
            'data_fim': data_fim or default_fim.isoformat(),
            'saldo_inicial': saldo_inicial or '0.00',
            'entidade': entidade or '',
            'pagamento': pagamento or '',
        }

        preserved_qs = {k: v for k, v in preserved.items() if v}

        # --- 2. Query base ---
        rec_qs = Titulosreceber.objects.using(self.db_alias).filter(
            titu_aber__in=['A', 'P', 'B']
        )

        pag_qs = Titulospagar.objects.using(self.db_alias).filter(
            titu_aber__in=['A', 'P', 'B']
        )

        if self.empresa_id:
            rec_qs = rec_qs.filter(titu_empr=self.empresa_id)
            pag_qs = pag_qs.filter(titu_empr=self.empresa_id)

        if self.filial_id:
            rec_qs = rec_qs.filter(titu_fili=self.filial_id)
            pag_qs = pag_qs.filter(titu_fili=self.filial_id)

        # --- 3. Filtro por vencimento ---
        rec_qs = rec_qs.filter(titu_venc__range=(preserved['data_ini'], preserved['data_fim']))
        pag_qs = pag_qs.filter(titu_venc__range=(preserved['data_ini'], preserved['data_fim']))

        # Entidade (join manual via tabela entidades)
        if preserved['entidade']:
            ent_qs = Entidades.objects.using(self.db_alias).filter(
                enti_nome__icontains=preserved['entidade'],
            )
            if self.empresa_id:
                ent_qs = ent_qs.filter(enti_empr=self.empresa_id)
            ent_ids = list(ent_qs.values_list('enti_clie', flat=True)[:5000])
            rec_qs = rec_qs.filter(titu_clie__in=ent_ids)
            pag_qs = pag_qs.filter(titu_forn__in=ent_ids)

        # Pagamento (forma)
        if preserved['pagamento']:
            rec_qs = rec_qs.filter(titu_form_reci=preserved['pagamento'])
            pag_qs = pag_qs.filter(titu_form_reci=preserved['pagamento'])

        # --- 4. naolistarpagar ---
        situ_nao_listar_sq = Situacoes.objects.using(self.db_alias).filter(
            situ_codi=OuterRef('titu_situ')
        ).values('situ_nao_list_cp')[:1]

        pag_qs = pag_qs.annotate(
            nao_listar=Subquery(situ_nao_listar_sq)
        ).filter(
            Q(nao_listar=False) | Q(nao_listar__isnull=True)
        )

        rec_ids = set(rec_qs.values_list('titu_clie', flat=True).distinct())
        pag_ids = set(pag_qs.values_list('titu_forn', flat=True).distinct())
        ent_ids = {i for i in (rec_ids | pag_ids) if i is not None}

        entidades_qs = Entidades.objects.using(self.db_alias).filter(enti_clie__in=ent_ids)
        if self.empresa_id:
            entidades_qs = entidades_qs.filter(enti_empr=self.empresa_id)
        ent_listas = list(entidades_qs.values('enti_clie', 'enti_nome').order_by('enti_nome')[:5000])

        rec_forms = set(rec_qs.values_list('titu_form_reci', flat=True).distinct())
        pag_forms = set(pag_qs.values_list('titu_form_reci', flat=True).distinct())
        pag_listas = sorted([f for f in (rec_forms | pag_forms) if f])

        # --- 6. Agregação mensal (fonte única para cards e tabela) ---
        rec_mensal = rec_qs.annotate(
            mes=TruncMonth('titu_venc')
        ).values('mes').annotate(
            valor=Sum('titu_valo')
        )

        pag_mensal = pag_qs.annotate(
            mes=TruncMonth('titu_venc')
        ).values('mes').annotate(
            valor=Sum('titu_valo')
        )

        # Totais com base nas mesmas agregações exibidas na tabela
        total_receita = float(sum(float(r['valor'] or 0) for r in rec_mensal))
        total_despesa = float(sum(float(p['valor'] or 0) for p in pag_mensal))
        resultado_liquido = float(total_receita) - float(total_despesa)

        try:
            saldo_inicial_val = float(preserved['saldo_inicial'])
        except Exception:
            saldo_inicial_val = 0.0
        saldo_final = saldo_inicial_val + resultado_liquido

        mensal_map = {}

        for r in rec_mensal:
            mensal_map[r['mes']] = {
                'mes': r['mes'],
                'receita': float(r['valor'] or 0),
                'despesa': 0.0,
            }

        for p in pag_mensal:
            entry = mensal_map.get(
                p['mes'],
                {'mes': p['mes'], 'receita': 0.0, 'despesa': 0.0}
            )
            entry['despesa'] = float(p['valor'] or 0)
            mensal_map[p['mes']] = entry

        movimentos_mensais = []
        for _, m in sorted(mensal_map.items(), key=lambda x: x[0]):
            m['resultado'] = m['receita'] - m['despesa']
            movimentos_mensais.append(m)

        # --- 8. Contexto ---
        context.update({
            'slug': self.slug,
            'empresa_id': self.empresa_id,
            'filial_id': self.filial_id,
            'filters': preserved,
            'preserved_query': urlencode(preserved_qs),
            'ent_listas': ent_listas,
            'pag_listas': pag_listas,
            'total_receita': total_receita,
            'total_despesa': total_despesa,
            'resultado_liquido': resultado_liquido,
            'saldo_inicial': saldo_inicial_val,
            'saldo_final': saldo_final,
            'movimentos_mensais': movimentos_mensais,
        })

        return context


class BaixasEmMassaPageView(DBAndSlugMixin, TemplateView):
    template_name = "Financeiro/baixas_em_massa.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["empresa_id"] = self.empresa_id
        context["filial_id"] = self.filial_id
        return context

class DetalhesCompetenciaView(DBAndSlugMixin, View):
    def get(self, request, year, month, *args, **kwargs):
        y = int(year)
        m = int(month)
        start = date(y, m, 1)
        end = date(y, m, monthrange(y, m)[1])

        rec_qs = Titulosreceber.objects.using(self.db_alias).filter(titu_aber__in=['A', 'P', 'B'])
        pag_qs = Titulospagar.objects.using(self.db_alias).filter(titu_aber__in=['A', 'P', 'B'])

        if self.empresa_id:
            rec_qs = rec_qs.filter(titu_empr=self.empresa_id)
            pag_qs = pag_qs.filter(titu_empr=self.empresa_id)

        if self.filial_id:
            rec_qs = rec_qs.filter(titu_fili=self.filial_id)
            pag_qs = pag_qs.filter(titu_fili=self.filial_id)

        rec_qs = rec_qs.filter(
            titu_venc__range=(start, end)
        )

        recebido_ate_sq = (
            Baretitulos.objects.using(self.db_alias)
            .filter(
                bare_empr=OuterRef('titu_empr'),
                bare_fili=OuterRef('titu_fili'),
                bare_clie=OuterRef('titu_clie'),
                bare_titu=OuterRef('titu_titu'),
                bare_seri=OuterRef('titu_seri'),
                bare_parc=OuterRef('titu_parc'),
                bare_dpag__lte=end,
            )
            .values('bare_titu')
            .annotate(total=Sum('bare_sub_tota'))
            .values('total')[:1]
        )

        rec_qs = rec_qs.annotate(
            recebido_ate=Subquery(recebido_ate_sq, output_field=DecimalField(max_digits=15, decimal_places=2)),
        ).annotate(
            saldo_aberto=Greatest(
                F('titu_valo') - Coalesce(F('recebido_ate'), Value(0)),
                Value(0),
            )
        ).only(
            'titu_titu','titu_parc','titu_seri','titu_emis','titu_venc','titu_valo','titu_clie'
        )

        pag_qs = pag_qs.filter(
            titu_venc__range=(start, end)
        )
        # Aplicar mesmo filtro de "nao listar pagar" usado em FluxoCompetenciaView
        situ_nao_listar_sq = Situacoes.objects.using(self.db_alias).filter(
            situ_codi=OuterRef('titu_situ')
        ).values('situ_nao_list_cp')[:1]
        pag_qs = pag_qs.annotate(
            nao_listar=Subquery(situ_nao_listar_sq)
        ).filter(
            Q(nao_listar=False) | Q(nao_listar__isnull=True)
        ).annotate(
            saldo_aberto=Func(
                F('titu_empr'),
                F('titu_fili'),
                F('titu_forn'),
                F('titu_titu'),
                F('titu_seri'),
                F('titu_parc'),
                Value(end),
                function='fnc_saldo_pagar',
                output_field=DecimalField(max_digits=15, decimal_places=2),
            )
        ).only(
            'titu_titu','titu_parc','titu_seri','titu_emis','titu_venc','titu_forn','titu_valo'
        )

        rec_rows = list(rec_qs[:500])
        pag_rows = list(pag_qs[:500])

        ent_ids = (
            {r.titu_clie for r in rec_rows if getattr(r, 'titu_clie', None) is not None}
            | {p.titu_forn for p in pag_rows if getattr(p, 'titu_forn', None) is not None}
        )
        ent_qs = Entidades.objects.using(self.db_alias).filter(enti_clie__in=ent_ids)
        if self.empresa_id:
            ent_qs = ent_qs.filter(enti_empr=self.empresa_id)
        nomes = {e['enti_clie']: e['enti_nome'] for e in ent_qs.values('enti_clie', 'enti_nome')}

        receitas = [
            {
                'titulo': r.titu_titu,
                'parcela': r.titu_parc,
                'serie': r.titu_seri,
                'entidade': nomes.get(getattr(r, 'titu_clie', None), ''),
                'emissao': r.titu_emis,
                'vencimento': r.titu_venc,
                'valor': float(r.titu_valo or 0),
                'saldo_aberto': float(getattr(r, 'saldo_aberto', 0) or 0),
            }
            for r in rec_rows
        ]

        despesas = [
            {
                'titulo': p.titu_titu,
                'parcela': p.titu_parc,
                'serie': p.titu_seri,
                'entidade': nomes.get(getattr(p, 'titu_forn', None), ''),
                'emissao': p.titu_emis,
                'vencimento': p.titu_venc,
                'valor': float(p.titu_valo or 0),
                'saldo_aberto': float(getattr(p, 'saldo_aberto', 0) or 0),
            }
            for p in pag_rows
        ]

        total_receita = sum(r['valor'] for r in receitas)
        total_despesa = sum(d['valor'] for d in despesas)

        return JsonResponse({
            'receitas': receitas,
            'despesas': despesas,
            'totais': {
                'receita': total_receita,
                'despesa': total_despesa,
                'resultado': total_receita - total_despesa,
            }
        })


class DetalhesCaixaView(DBAndSlugMixin, View):
    def get(self, request, year, month, *args, **kwargs):
        y = int(year)
        m = int(month)
        start = date(y, m, 1)
        end = date(y, m, monthrange(y, m)[1])

        rec_qs = Baretitulos.objects.using(self.db_alias)
        pag_qs = Bapatitulos.objects.using(self.db_alias)

        if self.empresa_id:
            rec_qs = rec_qs.filter(bare_empr=self.empresa_id)
            pag_qs = pag_qs.filter(bapa_empr=self.empresa_id)
        if self.filial_id:
            rec_qs = rec_qs.filter(bare_fili=self.filial_id)
            pag_qs = pag_qs.filter(bapa_fili=self.filial_id)

        rec_rows = list(
            rec_qs.filter(bare_dpag__range=(start, end)).only(
                'bare_titu', 'bare_parc', 'bare_seri', 'bare_dpag', 'bare_sub_tota', 'bare_clie'
            )[:500]
        )
        pag_rows = list(
            pag_qs.filter(bapa_dpag__range=(start, end)).only(
                'bapa_titu', 'bapa_parc', 'bapa_seri', 'bapa_dpag', 'bapa_sub_tota', 'bapa_forn'
            )[:500]
        )

        ent_ids = (
            {r.bare_clie for r in rec_rows if getattr(r, 'bare_clie', None) is not None}
            | {p.bapa_forn for p in pag_rows if getattr(p, 'bapa_forn', None) is not None}
        )
        ent_qs = Entidades.objects.using(self.db_alias).filter(enti_clie__in=ent_ids)
        if self.empresa_id:
            ent_qs = ent_qs.filter(enti_empr=self.empresa_id)
        nomes = {e['enti_clie']: e['enti_nome'] for e in ent_qs.values('enti_clie', 'enti_nome')}

        recebimentos = [
            {
                'titulo': r.bare_titu,
                'parcela': r.bare_parc,
                'serie': r.bare_seri,
                'entidade': nomes.get(getattr(r, 'bare_clie', None), ''),
                'data_pagamento': r.bare_dpag,
                'valor': float(getattr(r, 'bare_sub_tota', 0) or 0),
            }
            for r in rec_rows
        ]
        pagamentos = [
            {
                'titulo': p.bapa_titu,
                'parcela': p.bapa_parc,
                'serie': p.bapa_seri,
                'entidade': nomes.get(getattr(p, 'bapa_forn', None), ''),
                'data_pagamento': p.bapa_dpag,
                'valor': float(getattr(p, 'bapa_sub_tota', 0) or 0),
            }
            for p in pag_rows
        ]

        total_receb = sum(item['valor'] for item in recebimentos)
        total_paga = sum(item['valor'] for item in pagamentos)

        return JsonResponse({
            'recebimentos': recebimentos,
            'pagamentos': pagamentos,
            'totais': {
                'recebimentos': total_receb,
                'pagamentos': total_paga,
                'saldo': total_receb - total_paga,
            }
        })



class InadimplentesView(DBAndSlugMixin, View):
    def get(self, request, year, month, *args, **kwargs):
        y = int(year)
        m = int(month)
        start = date(y, m, 1)
        end = date(y, m, monthrange(y, m)[1])
        empresa = self.empresa_id or None
        filial = self.filial_id or None

        inad_qs = Titulospagar.objects.using(self.db_alias).filter(
            titu_situ=1,
            titu_emit__isnull=False,
            titu_forn__isnull=False,
            titu_venc__lte=end,
            titu_empr=empresa,
            titu_fili=filial,
        ).annotate(
            saldo_a_pagar=Func(
                F('titu_empr'),
                F('titu_fili'),
                F('titu_forn'),
                F('titu_titu'),
                F('titu_seri'),
                F('titu_parc'),
                Value(end),
                function='fnc_saldo_pagar',
                output_field=DecimalField(max_digits=15, decimal_places=2),
            )
        ).only(
            'titu_titu','titu_empr','titu_fili','titu_forn','titu_parc','titu_seri','titu_emis','titu_venc','saldo_a_pagar'
        )

        inadimplentes = [
            {
                'titulo': p.titu_titu,
                'empresa': p.titu_empr,
                'filial': p.titu_fili,
                'fornecedor': p.titu_forn,
                'parcela': p.titu_parc,
                'serie': p.titu_seri,
                'emissao': p.titu_emis,
                'vencimento': p.titu_venc,
                'valor': float(p.saldo_a_pagar or 0),
            }
            for p in inad_qs[:500]
        ]
        
        total_inadimplentes = sum(item['valor'] for item in inadimplentes)
        return JsonResponse({
            'inadimplentes': inadimplentes,
            'totais': {
                'inadimplentes': total_inadimplentes,
            }
        })
        
