from django.views.generic import TemplateView
from django.views import View
from django.http import JsonResponse
from datetime import date
from calendar import monthrange
from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.utils.http import urlencode
from django.utils import timezone
from core.utils import get_licenca_db_config
from contas_a_receber.models import Baretitulos, Titulosreceber
from contas_a_pagar.models import Bapatitulos, Titulospagar



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



class FluxoCompetenciaView(DBAndSlugMixin, TemplateView):
    template_name = 'Financeiro/fluxo_competencia.html' 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # --- 1. Parâmetros e Filtros ---
        data_ini = self.request.GET.get('data_ini')
        data_fim = self.request.GET.get('data_fim')
        saldo_inicial = self.request.GET.get('saldo_inicial')

        # Defaults para o mês corrente
        today = timezone.now().date()
        default_ini = today.replace(day=1)
        default_fim = today

        preserved = {
            'data_ini': data_ini or default_ini.isoformat(),
            'data_fim': data_fim or default_fim.isoformat(),
            'saldo_inicial': saldo_inicial or '0.00',
        }
        preserved_qs = {k: v for k, v in preserved.items() if v}

        # --- 2. Queries por Competência ---
        # Usamos os MODELS de Títulos ABERTO/GERADO, não os de Baixa (Baretitulos/Bapatitulos)
        
        rec_qs = Titulosreceber.objects.using(self.db_alias)
        pag_qs = Titulospagar.objects.using(self.db_alias)

        if self.empresa_id:
            rec_qs = rec_qs.filter(titu_empr=self.empresa_id)
            pag_qs = pag_qs.filter(titu_empr=self.empresa_id)
        if self.filial_id:
            rec_qs = rec_qs.filter(titu_fili=self.filial_id)
            pag_qs = pag_qs.filter(titu_fili=self.filial_id)

        # Filtro CRÍTICO: Usamos a data de EMISSÃO/COMPETÊNCIA
        rec_qs = rec_qs.filter(titu_emis__range=(preserved['data_ini'], preserved['data_fim']))
        pag_qs = pag_qs.filter(titu_emis__range=(preserved['data_ini'], preserved['data_fim']))

        # --- 3. Totais do Período ---
        # Usamos o campo de valor principal
        total_receita = rec_qs.aggregate(
            total=Sum('titu_valo')
        )['total'] or 0

        total_despesa = pag_qs.aggregate(
            total=Sum('titu_valo')
        )['total'] or 0

        # O Resultado de Competência não usa Saldo Inicial
        resultado_liquido = float(total_receita) - float(total_despesa)

        try:
            saldo_inicial_val = float(preserved['saldo_inicial'])
        except Exception:
            saldo_inicial_val = 0.0

        saldo_final = (saldo_inicial_val or 0) + float(resultado_liquido)
        
        # --- 4. Agregações Mensais (Visualização do Resultado) ---
        
        # Agrega pelo Mês de Emissão/Competência
        rec_mensal = rec_qs.annotate(mes=TruncMonth('titu_emis')).values('mes').annotate(valor=Sum('titu_valo'))
        pag_mensal = pag_qs.annotate(mes=TruncMonth('titu_emis')).values('mes').annotate(valor=Sum('titu_valo'))

        # Lógica de mesclagem (similar ao seu código)
        mensal_map = {}
        for r in rec_mensal:
            mensal_map[r['mes']] = {'mes': r['mes'], 'receita': float(r['valor'] or 0), 'despesa': 0.0}
        for p in pag_mensal:
            entry = mensal_map.get(p['mes'], {'mes': p['mes'], 'receita': 0.0, 'despesa': 0.0})
            entry['despesa'] = float(p['valor'] or 0)
            mensal_map[p['mes']] = entry

        movimentos_mensais = []
        for _, m in sorted(mensal_map.items(), key=lambda x: x[0]):
            m['resultado'] = m['receita'] - m['despesa']
            movimentos_mensais.append(m)

        # --- 5. Contexto ---
        context.update({
            'slug': self.slug,
            'empresa_id': self.empresa_id,
            'filial_id': self.filial_id,
            'filters': preserved,
            'preserved_query': urlencode(preserved_qs),
            'total_receita': total_receita,
            'total_despesa': total_despesa,
            'resultado_liquido': resultado_liquido,
            'saldo_inicial': saldo_inicial_val,
            'saldo_final': saldo_final,
            'movimentos_mensais': movimentos_mensais,
            # ... suas variáveis de slug/empresa/filial
        })
        return context


class DetalhesCompetenciaView(DBAndSlugMixin, View):
    def get(self, request, year, month, *args, **kwargs):
        y = int(year)
        m = int(month)
        start = date(y, m, 1)
        end = date(y, m, monthrange(y, m)[1])

        rec_qs = Titulosreceber.objects.using(self.db_alias)
        pag_qs = Titulospagar.objects.using(self.db_alias)

        if self.empresa_id:
            rec_qs = rec_qs.filter(titu_empr=self.empresa_id)
            pag_qs = pag_qs.filter(titu_empr=self.empresa_id)
        if self.filial_id:
            rec_qs = rec_qs.filter(titu_fili=self.filial_id)
            pag_qs = pag_qs.filter(titu_fili=self.filial_id)

        rec_qs = rec_qs.filter(titu_emis__range=(start, end)).only('titu_titu','titu_parc','titu_seri','titu_emis','titu_venc','titu_valo')
        pag_qs = pag_qs.filter(titu_emis__range=(start, end)).only('titu_titu','titu_parc','titu_seri','titu_emis','titu_venc','titu_valo')

        receitas = [
            {
                'titulo': r.titu_titu,
                'parcela': r.titu_parc,
                'serie': r.titu_seri,
                'emissao': r.titu_emis,
                'vencimento': r.titu_venc,
                'valor': float(r.titu_valo or 0),
            }
            for r in rec_qs[:500]
        ]
        despesas = [
            {
                'titulo': p.titu_titu,
                'parcela': p.titu_parc,
                'serie': p.titu_seri,
                'emissao': p.titu_emis,
                'vencimento': p.titu_venc,
                'valor': float(p.titu_valo or 0),
            }
            for p in pag_qs[:500]
        ]

        total_receita = sum(item['valor'] for item in receitas)
        total_despesa = sum(item['valor'] for item in despesas)

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

        rec_qs = rec_qs.filter(bare_dpag__range=(start, end)).only('bare_titu','bare_parc','bare_seri','bare_dpag','bare_sub_tota')
        pag_qs = pag_qs.filter(bapa_dpag__range=(start, end)).only('bapa_titu','bapa_parc','bapa_seri','bapa_dpag','bapa_sub_tota')

        recebimentos = [
            {
                'titulo': r.bare_titu,
                'parcela': r.bare_parc,
                'serie': r.bare_seri,
                'data_pagamento': r.bare_dpag,
                'valor': float(getattr(r, 'bare_sub_tota', 0) or 0),
            }
            for r in rec_qs[:500]
        ]
        pagamentos = [
            {
                'titulo': p.bapa_titu,
                'parcela': p.bapa_parc,
                'serie': p.bapa_seri,
                'data_pagamento': p.bapa_dpag,
                'valor': float(getattr(p, 'bapa_sub_tota', 0) or 0),
            }
            for p in pag_qs[:500]
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
