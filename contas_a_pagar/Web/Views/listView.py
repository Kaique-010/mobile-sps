from django.views.generic import ListView
from ..mixin import DBAndSlugMixin
from django.db import connections
from django.db.models import Sum, Q
from django.http import JsonResponse
from django.conf import settings
from django.shortcuts import render
from django.utils.http import urlencode
from django.utils import timezone
from core.utils import get_licenca_db_config
from ...models import Titulospagar, Bapatitulos
from Entidades.models import Entidades
from CentrodeCustos.models import Centrodecustos
from Licencas.models import Empresas, Filiais
from datetime import date
from django.utils.timezone import now


class TitulosPagarListView(DBAndSlugMixin, ListView):
    model = Titulospagar
    template_name = 'ContasAPagar/titulos_pagar_list.html'
    context_object_name = 'titulos'
    paginate_by = 20

    def get_queryset(self):
        # Prioridade para GET params no filtro
        try:
            if self.request.GET.get('titu_empr'):
                self.empresa_id = int(self.request.GET.get('titu_empr'))
            if self.request.GET.get('titu_fili'):
                self.filial_id = int(self.request.GET.get('titu_fili'))
        except (ValueError, TypeError):
            pass

        # Validação de consistência Filial x Empresa
        if self.empresa_id and self.filial_id:
            filial_obj = Filiais.objects.using(self.db_alias).filter(empr_empr=self.filial_id).first()
            if filial_obj and str(filial_obj.empr_codi) != str(self.empresa_id):
                valid = Filiais.objects.using(self.db_alias).filter(empr_codi=self.empresa_id).first()
                self.filial_id = valid.empr_empr if valid else None

        qs = Titulospagar.objects.using(self.db_alias).all()

        # Captura os parâmetros de filtro da URL
        fornecedor_id = self.request.GET.get('titu_forn')
        fornecedor_nome = self.request.GET.get('fornecedor_nome')
        titu_cecu = self.request.GET.get('titu_cecu')
        nome_centro_custo = self.request.GET.get('nome_centro_custo')
        status_aber = self.request.GET.get('titu_aber')
        venc_ini = self.request.GET.get('venc_ini')
        venc_fim = self.request.GET.get('venc_fim')
        serie = self.request.GET.get('titu_seri')
        titu_titu = self.request.GET.get('titu_titu')

        # Se NÃO houver filtro de data explícito, aplica o padrão (mês atual até hoje)
        if not venc_ini and not venc_fim:
            hoje = now().date()
            inicio_mes = date(hoje.year, hoje.month, 1)
            qs = qs.filter(
                Q(titu_venc__isnull=True) | Q(titu_venc__range=(inicio_mes, hoje))
            )

        # Seleciona apenas os campos necessários
        qs = qs.only(
            'titu_empr',
            'titu_fili',
            'titu_forn',
            'titu_titu',
            'titu_seri',
            'titu_parc',
            'titu_valo',
            'titu_venc',
            'titu_emis',
            'titu_aber',
            'titu_cecu',
        )

        # Aplica os filtros recebidos

        if self.empresa_id:
            qs = qs.filter(titu_empr=self.empresa_id)
        if self.filial_id:
            qs = qs.filter(titu_fili=self.filial_id)
        if fornecedor_id:
            qs = qs.filter(titu_forn=fornecedor_id)
        if status_aber:
            qs = qs.filter(titu_aber=status_aber)
        if venc_ini:
            qs = qs.filter(titu_venc__gte=venc_ini)
        if venc_fim:
            qs = qs.filter(titu_venc__lte=venc_fim)
        if serie:
            qs = qs.filter(titu_seri__iexact=serie)
        if titu_titu:
            qs = qs.filter(titu_titu__iexact=titu_titu)
        if titu_cecu:
            qs = qs.filter(titu_cecu__iexact=titu_cecu)

        # Filtro por nome do fornecedor via Entidades
        if fornecedor_nome:
            entidades_qs = Entidades.objects.using(self.db_alias).filter(enti_nome__icontains=fornecedor_nome)
            fornecedor_ids = list(entidades_qs.values_list('enti_clie', flat=True))
            if fornecedor_ids:
                qs = qs.filter(titu_forn__in=fornecedor_ids)
            else:
                qs = qs.none()
        
        # Filtro por nome do Centro de Custo
        if nome_centro_custo:
            centro_custos_qs = Centrodecustos.objects.using(self.db_alias).filter(cecu_nome__icontains=nome_centro_custo)
            titu_cecu_ids = list(centro_custos_qs.values_list('cecu_redu', flat=True))
            if titu_cecu_ids:
                qs = qs.filter(titu_cecu__in=titu_cecu_ids)
            else:
                qs = qs.none()
        
        return qs.order_by('titu_venc', 'titu_titu')
      

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_qs = context.get('titulos')
        # Usar o queryset completo (com os mesmos filtros) para calcular os totais
        qs_all = self.get_queryset()

        # Totais básicos
        total_geral = qs_all.aggregate(total=Sum('titu_valo'))['total'] or 0
        total_quitado = qs_all.filter(titu_aber='T').aggregate(total=Sum('titu_valo'))['total'] or 0
        titulos_parciais = list(qs_all.filter(titu_aber='P').values(
            'titu_empr', 'titu_fili', 'titu_forn', 'titu_titu', 'titu_seri', 'titu_parc', 'titu_valo'
        ))

        # Buscar pagamentos das baixas referentes aos títulos parciais
        pagamentos_map = {}
        if titulos_parciais:
            empr = self.empresa_id
            fili = self.filial_id
            forn_ids = list({t['titu_forn'] for t in titulos_parciais if t['titu_forn']})
            titu_ids = list({t['titu_titu'] for t in titulos_parciais if t['titu_titu']})
            seri_ids = list({t['titu_seri'] for t in titulos_parciais if t['titu_seri']})
            parc_ids = list({t['titu_parc'] for t in titulos_parciais if t['titu_parc']})

            bapa_qs = Bapatitulos.objects.using(self.db_alias)
            if empr:
                bapa_qs = bapa_qs.filter(bapa_empr=empr)
            if fili:
                bapa_qs = bapa_qs.filter(bapa_fili=fili)
            if forn_ids:
                bapa_qs = bapa_qs.filter(bapa_forn__in=forn_ids)
            if titu_ids:
                bapa_qs = bapa_qs.filter(bapa_titu__in=titu_ids)
            if seri_ids:
                bapa_qs = bapa_qs.filter(bapa_seri__in=seri_ids)
            if parc_ids:
                bapa_qs = bapa_qs.filter(bapa_parc__in=parc_ids)

            for row in bapa_qs.values('bapa_empr','bapa_fili','bapa_forn','bapa_titu','bapa_seri','bapa_parc')\
                               .annotate(total_pago=Sum('bapa_sub_tota')):
                chave = (row['bapa_empr'], row['bapa_fili'], row['bapa_forn'], row['bapa_titu'], row['bapa_seri'], row['bapa_parc'])
                pagamentos_map[chave] = row['total_pago'] or 0

        # Calcula pago parcial e em aberto (restante) por título parcial
        total_pago_parcial = 0
        total_restante_parcial = 0
        for t in titulos_parciais:
            chave = (t['titu_empr'], t['titu_fili'], t['titu_forn'], t['titu_titu'], t['titu_seri'], t['titu_parc'])
            pago = pagamentos_map.get(chave, 0) or 0
            total_pago_parcial += pago
            restante = (t['titu_valo'] or 0) - (pago or 0)
            if restante > 0:
                total_restante_parcial += restante

        # Consolida métricas solicitadas
        total_pago = total_quitado + total_pago_parcial
        total_em_aberto = max((total_geral or 0) - (total_pago or 0), 0)
        percent_pago = float(((total_pago or 0) / (total_geral or 1)) * 100) if total_geral else 0.0
        percent_a_pagar = float(100.0 - percent_pago) if total_geral else 0.0
        fornecedor_ids = set()
        cecu_ids = set()
        for t in page_qs:
            if t.titu_forn:
                fornecedor_ids.add(t.titu_forn)
            if t.titu_cecu:
                cecu_ids.add(t.titu_cecu)

        entidades_map = {}
        if fornecedor_ids:
            ents = Entidades.objects.using(self.db_alias).filter(enti_clie__in=list(fornecedor_ids))
            entidades_map = {e.enti_clie: e.enti_nome for e in ents}

        centros_map = {}
        if cecu_ids:
            centros = Centrodecustos.objects.using(self.db_alias).filter(cecu_redu__in=list(cecu_ids))
            centros_map = {c.cecu_redu: c.cecu_nome for c in centros}

        # Anota nome do fornecedor em cada título para fácil renderização no template
        for t in page_qs:
            setattr(t, 'fornecedor_nome', entidades_map.get(t.titu_forn, ''))
            setattr(t, 'nome_centro_custo', centros_map.get(t.titu_cecu, ''))

        # Preserva filtros na paginação
        preserved = {
            'titu_forn': self.request.GET.get('titu_forn') or '',
            'fornecedor_nome': self.request.GET.get('fornecedor_nome') or '',
            'titu_aber': self.request.GET.get('titu_aber') or '',
            'venc_ini': self.request.GET.get('venc_ini') or '',
            'venc_fim': self.request.GET.get('venc_fim') or '',
            'titu_seri': self.request.GET.get('titu_seri') or '',
            'titu_titu': self.request.GET.get('titu_titu') or '',
            'titu_empr': self.empresa_id,
            'titu_fili': self.filial_id,
        }
        preserved_qs = {k: v for k, v in preserved.items() if v}

        # Carregar listas para os selects de filtro
        try:
            context['empresas'] = Empresas.objects.using(self.db_alias).all().order_by('empr_nome')
            
            filiais_qs = Filiais.objects.using(self.db_alias).all()
            if self.empresa_id:
                filiais_qs = filiais_qs.filter(empr_codi=self.empresa_id)
            context['filiais'] = filiais_qs.order_by('empr_nome')
        except Exception:
            context['empresas'] = []
            context['filiais'] = []

        context.update({
            'slug': self.slug,
            'empresa_id': self.empresa_id,
            'filial_id': self.filial_id,
            'preserved_query': urlencode(preserved_qs),
            'filters': preserved,
            # Novas métricas para os cards do topo
            'total_geral': total_geral,
            'total_pago': total_pago,
            'total_em_aberto': total_em_aberto,
            'percent_pago': percent_pago,
            'percent_a_pagar': percent_a_pagar,
        })
        return context

class TitulosPagarParcelasListView(TitulosPagarListView):
    template_name = 'ContasAPagar/parcelas_a_pagar_list.html'

def autocomplete_fornecedores(request, slug=None):
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
