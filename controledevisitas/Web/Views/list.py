from django.views.generic import ListView, TemplateView
from core.utils import get_licenca_db_config
from controledevisitas.models import Controlevisita, ItensVisita
from Produtos.models import Produtos


class ControleVisitaListView(ListView):
    template_name = 'ControleDeVisitas/visitas_cards.html'
    context_object_name = 'visitas'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug')
        self.db_alias = get_licenca_db_config(request)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = Controlevisita.objects.using(self.db_alias).select_related('ctrl_cliente', 'ctrl_vendedor', 'ctrl_etapa').all()
        cliente = self.request.GET.get('cliente')
        vendedor = self.request.GET.get('vendedor')
        if cliente:
            qs = qs.filter(ctrl_cliente__enti_nome__icontains=cliente)
        if vendedor:
            qs = qs.filter(ctrl_vendedor__enti_nome__icontains=vendedor)
        return qs.order_by('-ctrl_data', '-ctrl_numero')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        return ctx


class ProximasVisitasDashboardView(TemplateView):
    template_name = 'ControleDeVisitas/visitas_dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug')
        self.db_alias = get_licenca_db_config(request)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from datetime import date, timedelta
        ctx = super().get_context_data(**kwargs)
        hoje = date.today()
        visitas = Controlevisita.objects.using(self.db_alias).select_related('ctrl_cliente','ctrl_vendedor').filter(ctrl_prox_visi__gte=hoje).order_by('ctrl_prox_visi')[:100]
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
        ctx['slug'] = self.slug
        ctx['proximas'] = proximas
        ctx['total'] = len(proximas)
        return ctx


class ControleVisitaResumoView(TemplateView):
    template_name = 'ControleDeVisitas/visita_resumo.html'

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug')
        self.ctrl_id = kwargs.get('ctrl_id')
        self.db_alias = get_licenca_db_config(request)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        visita = Controlevisita.objects.using(self.db_alias).select_related('ctrl_cliente', 'ctrl_vendedor', 'ctrl_etapa').get(ctrl_id=self.ctrl_id)
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
