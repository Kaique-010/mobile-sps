from django.views.generic import ListView, TemplateView
from django.db.models import Sum, Count
from core.utils import get_licenca_db_config
from Produtos.models import Produtos
from coletaestoque.models import ColetaEstoque


class ColetaListView(ListView):
    model = ColetaEstoque
    template_name = 'ColetaEstoque/coletas_list.html'
    context_object_name = 'coletas'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug')
        self.db_alias = get_licenca_db_config(request)
        self.empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa')
        self.filial_id = request.session.get('filial_id') or request.headers.get('X-Filial')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = ColetaEstoque.objects.using(self.db_alias).all()
        if self.empresa_id:
            qs = qs.filter(cole_empr=int(self.empresa_id))
        if self.filial_id:
            qs = qs.filter(cole_fili=int(self.filial_id))
        codigo_produto = (self.request.GET.get('produto') or '').strip()
        if codigo_produto:
            qs = qs.filter(cole_prod=codigo_produto)
        return qs.order_by('-cole_data_leit')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        produtos = Produtos.objects.using(self.db_alias).filter(
            prod_codi__in=list(set(self.object_list.values_list('cole_prod', flat=True)))
        )
        mapa = {p.prod_codi: {'nome': p.prod_nome, 'coba': p.prod_coba} for p in produtos}
        enriquecidas = []
        for c in self.object_list:
            prod = mapa.get(c.cole_prod, {})
            enriquecidas.append({
                'cole_prod': c.cole_prod,
                'prod_nome': prod.get('nome'),
                'prod_coba': prod.get('coba'),
                'cole_quan_lida': c.cole_quan_lida,
                'cole_data_leit': c.cole_data_leit,
                'cole_usua': c.cole_usua,
            })
        ctx['coletas_enriquecidas'] = enriquecidas
        return ctx


class ColetaResumoView(TemplateView):
    template_name = 'ColetaEstoque/coletas_resumo.html'

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug')
        self.db_alias = get_licenca_db_config(request)
        self.empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa')
        self.filial_id = request.session.get('filial_id') or request.headers.get('X-Filial')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        qs = ColetaEstoque.objects.using(self.db_alias).all()
        if self.empresa_id:
            qs = qs.filter(cole_empr=int(self.empresa_id))
        if self.filial_id:
            qs = qs.filter(cole_fili=int(self.filial_id))
        agrupado = qs.values('cole_prod').annotate(
            total_coletado=Sum('cole_quan_lida'),
            total_leituras=Count('id')
        )
        produtos = Produtos.objects.using(self.db_alias).filter(
            prod_codi__in=[x['cole_prod'] for x in agrupado]
        )
        mapa = {p.prod_codi: {'nome': p.prod_nome, 'coba': p.prod_coba} for p in produtos}
        resumo = []
        for item in agrupado:
            prod = mapa.get(item['cole_prod'], {})
            resumo.append({
                'prod_codi': item['cole_prod'],
                'prod_nome': prod.get('nome'),
                'prod_coba': prod.get('coba'),
                'total_coletado': item['total_coletado'],
                'total_leituras': item['total_leituras']
            })
        resumo.sort(key=lambda x: (x['prod_nome'] or ''))
        ctx['resumo'] = resumo
        return ctx
