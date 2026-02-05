from django.views.generic import ListView, TemplateView
from core.utils import get_licenca_db_config
from controledevisitas.models import Controlevisita, ItensVisita
from Produtos.models import Produtos
from logging import getLogger
from core.mixins.vendedor_mixin import VendedorEntidadeMixin
from core.decorator import ModuloRequeridoMixin
logger = getLogger(__name__)


class ControleVisitaListView(ModuloRequeridoMixin, VendedorEntidadeMixin, ListView):
    template_name = 'ControleDeVisitas/visitas_cards.html'
    context_object_name = 'visitas'
    paginate_by = 9
    modulo_requerido = 'controledevisitas'

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug')
        self.db_alias = get_licenca_db_config(request)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        
        empresa_id = int(self.request.session.get('empresa_id', 1))
        filial_id = int(self.request.session.get('filial_id', 1))
        qs = Controlevisita.objects.using(self.db_alias).select_related('ctrl_cliente', 'ctrl_vendedor', 'ctrl_etapa').filter(
            ctrl_empresa_id=empresa_id,
            ctrl_filial=filial_id,
        )
        qs = self.filter_por_vendedor(qs, 'ctrl_vendedor')
        logger.info(f'Queryset: {qs.query}')
        cliente = self.request.GET.get('cliente')
        vendedor = self.request.GET.get('vendedor')
        etapa = self.request.GET.get('etapa')
        data_inicio = self.request.GET.get('data_inicio')
        data_fim = self.request.GET.get('data_fim')
        if cliente:
            qs = qs.filter(ctrl_cliente__enti_nome__icontains=cliente)
        if vendedor:
            qs = qs.filter(ctrl_vendedor__enti_nome__icontains=vendedor)
        if etapa:
            qs = qs.filter(ctrl_etapa__etap_descricao__icontains=etapa)
        if data_inicio:
            qs = qs.filter(ctrl_data__gte=data_inicio)
        if data_fim:
            qs = qs.filter(ctrl_data__lte=data_fim)
        return qs.order_by('-ctrl_data', '-ctrl_numero')
    

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        # Funil por etapa
        empresa_id = int(self.request.session.get('empresa_id', 1))
        filial_id = int(self.request.session.get('filial_id', 1))
        base = Controlevisita.objects.using(self.db_alias).filter(
            ctrl_empresa_id=empresa_id,
            ctrl_filial=filial_id,
        )
        base = self.filter_por_vendedor(base, 'ctrl_vendedor')
        cliente = self.request.GET.get('cliente')
        vendedor = self.request.GET.get('vendedor')
        etapa = self.request.GET.get('etapa')
        data_inicio = self.request.GET.get('data_inicio')
        data_fim = self.request.GET.get('data_fim')
        if cliente:
            base = base.filter(ctrl_cliente__enti_nome__icontains=cliente)
        if vendedor:
            base = base.filter(ctrl_vendedor__enti_nome__icontains=vendedor)
        if etapa:
            base = base.filter(ctrl_etapa__etap_descricao__icontains=etapa)
        if data_inicio:
            base = base.filter(ctrl_data__gte=data_inicio)
        if data_fim:
            base = base.filter(ctrl_data__lte=data_fim)
        total = base.count() or 1
        from django.db.models import Count
        funil_rows = list(
            base.values('ctrl_etapa__etap_descricao').annotate(qtd=Count('ctrl_id')).order_by('ctrl_etapa__etap_descricao')
        )
        mapa = {
            'AGENDAMENTO': 'success',
            'CONTATO INICIAL': 'warning',
            'INVESTIGACAO': 'indigo',
            'INVESTIGAÇÃO': 'indigo',
            'LEAD': 'purple',
            'NEGOCIACAO': 'primary',
            'NEGOCIAÇÃO': 'primary',
            'ORÇAMENTOS GANHOS': 'success',
            'ORCAMENTOS GANHOS': 'success',
            'ORÇAMENTOS PERDIDOS': 'danger',
            'ORCAMENTOS PERDIDOS': 'danger',
            'POS VENDA - OCORRÊNCIAS GERAIS': 'teal',
            'POS VENDA - OCORRENCIAS GERAIS': 'teal',
            'PROSPECÇÃO': 'info',
            'PROSPECCAO': 'info',
            'PROSPECÇÕES': 'info',
            'PROSPECCÕES': 'info',
            'PRE-ORÇAMENTOS': 'amber',
            'PRE-ORCAMENTOS': 'amber',
            'PEDIDOS ANTIGOS PESQUISA': 'pink',
            'POSATORE OCORRÊNCIAS EM OBRAS.': 'warning',
            'POSATORE OCORRENCIAS EM OBRAS.': 'warning',
            'RT - RESERVA TÉCNICA.': 'amber',
            'RT - RESERVA TECNICA.': 'amber',
            'SAIDAS PARTICULARES': 'brown',
            'VISITA EXTERNA': 'cyan',
            'VISITA CLIENTE LOJA': 'slate',
            'ETAPA INICIAL DE CONTATOS': 'primary',
            'FLUXO GANHO': 'success',
            'PERDA': 'danger',
            'PERCA': 'danger',
            'FOLLOW UP': 'secondary',
        }
        palette = ['success','warning','info','primary','danger','indigo','purple','pink','teal','amber','brown','slate']
        ctx['funil'] = []
        for i, r in enumerate(funil_rows):
            lbl = r['ctrl_etapa__etap_descricao'] or 'Não informado'
            key = (lbl or '').upper()
            ctx['funil'].append({
                'label': lbl,
                'qtd': r['qtd'],
                'perc': round((r['qtd'] * 100.0) / total, 1),
                'color': mapa.get(key) or palette[i % len(palette)]
            })
        return ctx


class ProximasVisitasDashboardView(ModuloRequeridoMixin, VendedorEntidadeMixin, TemplateView):
    template_name = 'ControleDeVisitas/visitas_dashboard.html'
    modulo_requerido = 'controledevisitas'

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug')
        self.db_alias = get_licenca_db_config(request)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        
        from datetime import date, timedelta
        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)
        ctx = super().get_context_data(**kwargs)
        hoje = date.today()
        visitas = Controlevisita.objects.using(self.db_alias).select_related('ctrl_cliente','ctrl_vendedor').filter(
            ctrl_prox_visi__gte=hoje,
            ctrl_empresa_id=empresa_id,
            ctrl_filial=filial_id,
        ).order_by('ctrl_prox_visi')
        visitas = self.filter_por_vendedor(visitas, 'ctrl_vendedor')
        cliente = (self.request.GET.get('cliente') or '').strip()
        vendedor = (self.request.GET.get('vendedor') or '').strip()
        etapa = (self.request.GET.get('etapa') or '').strip()
        data_inicial = self.request.GET.get('data_inicio')
        data_final = self.request.GET.get('data_fim')
        if cliente:
            visitas = visitas.filter(ctrl_cliente__enti_nome__icontains=cliente)
        if vendedor:
            visitas = visitas.filter(ctrl_vendedor__enti_nome__icontains=vendedor)
        if etapa:
            visitas = visitas.filter(ctrl_etapa__etap_descricao__icontains=etapa)
        if data_inicial:
            visitas = visitas.filter(ctrl_data__gte=data_inicial)
        if data_final:
            visitas = visitas.filter(ctrl_data__lte=data_final)
        visitas = visitas[:100]
        # Métricas
        total_visitas = Controlevisita.objects.using(self.db_alias).filter(
            ctrl_empresa_id=empresa_id,
            ctrl_filial=filial_id,
        )
        total_visitas = self.filter_por_vendedor(total_visitas, 'ctrl_vendedor')
        if cliente:
            total_visitas = total_visitas.filter(ctrl_cliente__enti_nome__icontains=cliente)
        if vendedor:
            total_visitas = total_visitas.filter(ctrl_vendedor__enti_nome__icontains=vendedor)
        if etapa:
            total_visitas = total_visitas.filter(ctrl_etapa__etap_descricao__icontains=etapa)
        if data_inicial:
            total_visitas = total_visitas.filter(ctrl_data__gte=data_inicial)
        if data_final:
            total_visitas = total_visitas.filter(ctrl_data__lte=data_final)
        hoje_count = total_visitas.filter(ctrl_data=hoje).count()
        import datetime
        inicio_semana = hoje - datetime.timedelta(days=hoje.weekday())
        semana_count = total_visitas.filter(ctrl_data__gte=inicio_semana).count()
        mes_count = total_visitas.filter(ctrl_data__year=hoje.year, ctrl_data__month=hoje.month).count()
        km_total = 0
        for v in total_visitas.values('ctrl_km_inic', 'ctrl_km_fina'):
            if v['ctrl_km_inic'] is not None and v['ctrl_km_fina'] is not None:
                try:
                    km_total += float(v['ctrl_km_fina']) - float(v['ctrl_km_inic'])
                except Exception:
                    pass
        proximas = []
        for v in visitas:
            dias = (v.ctrl_prox_visi - hoje).days if v.ctrl_prox_visi else None
            if dias is None:
                badge = 'secondary'
            elif dias <= 3:
                badge = 'danger'
            elif dias <= 7:
                badge = 'warning'
            else:
                badge = 'secondary'
            proximas.append({
                'ctrl_id': v.ctrl_id,
                'ctrl_numero': v.ctrl_numero,
                'data': v.ctrl_data,
                'prox': v.ctrl_prox_visi,
                'dias_restantes': dias,
                'cliente': getattr(v.ctrl_cliente, 'enti_nome', None),
                'vendedor': getattr(v.ctrl_vendedor, 'enti_nome', None),
                'badge_class': badge,
            })
        # Funil para gráfico
        from django.db.models import Count
        funil_rows = list(
            total_visitas.values('ctrl_etapa__etap_descricao').annotate(qtd=Count('ctrl_id')).order_by('ctrl_etapa__etap_descricao')
        )
        mapa = {
            'AGENDAMENTO': '#19c37d',
            'CONTATO INICIAL': '#f0ad4e',
            'INVESTIGAÇÃO': '#6c5ce7',
            'INVESTIGACAO': '#6c5ce7',
            'LEAD': '#9b59b6',
            'NEGOCIACAO': '#5b8def',
            'NEGOCIAÇÃO': '#5b8def',
            'ORÇAMENTOS GANHOS': '#19c37d',
            'ORCAMENTOS GANHOS': '#19c37d',
            'ORÇAMENTOS PERDIDOS': '#ff6b6b',
            'ORCAMENTOS PERDIDOS': '#ff6b6b',
            'POS VENDA - OCORRÊNCIAS GERAIS': '#20c997',
            'POS VENDA - OCORRENCIAS GERAIS': '#20c997',
            'PROSPECÇÃO': '#22b7d8',
            'PROSPECCAO': '#22b7d8',
            'PROSPECÇÕES': '#22b7d8',
            'PROSPECCÕES': '#22b7d8',
            'PRE-ORÇAMENTOS': '#ffc107',
            'PRE-ORCAMENTOS': '#ffc107',
            'PEDIDOS ANTIGOS PESQUISA': '#ff7eb6',
            'POSATORE OCORRÊNCIAS EM OBRAS.': '#f0ad4e',
            'POSATORE OCORRENCIAS EM OBRAS.': '#f0ad4e',
            'RT - RESERVA TÉCNICA.': '#ffc107',
            'RT - RESERVA TECNICA.': '#ffc107',
            'SAIDAS PARTICULARES': '#8d6e63',
            'VISITA EXTERNA': '#22b7d8',
            'VISITA CLIENTE LOJA': '#7f8c8d',
            'ETAPA INICIAL DE CONTATOS': '#5b8def',
            'FLUXO GANHO': '#19c37d',
            'PERDA': '#ff6b6b',
            'PERCA': '#ff6b6b',
            'FOLLOW UP': '#a8b4c2',
        }
        palette = ['#19c37d','#f0ad4e','#22b7d8','#5b8def','#ff6b6b','#6c5ce7','#9b59b6','#ff7eb6','#20c997','#ffc107','#8d6e63','#7f8c8d']
        funil = []
        for i, r in enumerate(funil_rows):
            lbl = r['ctrl_etapa__etap_descricao'] or 'Não informado'
            key = (lbl or '').upper()
            funil.append({ 'label': lbl, 'qtd': r['qtd'], 'color': mapa.get(key) or palette[i % len(palette)] })

        ctx['slug'] = self.slug
        ctx['filtros'] = {
            'cliente': cliente,
            'vendedor': vendedor,
            'etapa': etapa,
            'data_inicio': data_inicial,
            'data_fim': data_final,
        }
        ctx['proximas'] = proximas
        ctx['total'] = len(proximas)
        ctx['metricas'] = {
            'total_visitas': total_visitas.count(),
            'hoje': hoje_count,
            'semana': semana_count,
            'mes': mes_count,
            'km_total': km_total,
        }
        # JSON serializado para uso seguro no template
        import json
        try:
            ctx['funil_json'] = json.dumps(funil)
        except Exception:
            ctx['funil_json'] = '[]'
        ctx['funil'] = funil
        return ctx


class ControleVisitaResumoView(ModuloRequeridoMixin, VendedorEntidadeMixin, TemplateView):
    template_name = 'ControleDeVisitas/visita_resumo.html'
    modulo_requerido = 'controledevisitas'

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug')
        self.ctrl_id = kwargs.get('ctrl_id')
        self.db_alias = get_licenca_db_config(request)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)
        visita = Controlevisita.objects.using(self.db_alias).select_related('ctrl_cliente', 'ctrl_vendedor', 'ctrl_etapa').get(
            ctrl_id=self.ctrl_id,
            ctrl_empresa_id=int(empresa_id),
            ctrl_filial=int(filial_id)
        )  
        itens = list(ItensVisita.objects.using(self.db_alias).filter(item_visita=visita).order_by('-item_data'))
        prod_ids = [i.item_prod for i in itens if i.item_prod]
        produtos = Produtos.objects.using(self.db_alias).filter(prod_codi__in=prod_ids)
        mapa = {p.prod_codi: p for p in produtos}
        itens_enriquecidos = []
        for it in itens:
            p = mapa.get(it.item_prod)
            itens_enriquecidos.append({
                'item_id': it.item_id,
                'item_prod': it.item_prod,
                'produto_nome': getattr(p, 'prod_nome', None),
                'item_quan': it.item_quan,
                'item_unit': it.item_unit,
                'item_tota': it.item_tota,
                'item_unli': it.item_unli,
                'item_data': it.item_data,
                'item_obse': it.item_obse,
            })
        ctx['slug'] = self.slug
        ctx['visita'] = visita
        ctx['itens'] = itens_enriquecidos
        return ctx
