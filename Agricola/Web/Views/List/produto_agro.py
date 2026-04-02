from .base import BaseListView
from django.db.models import Q
from core.utils import get_licenca_db_config
from Agricola.models import ProdutoAgro, CategoriaProduto

class ProdutoAgroListView(BaseListView):
    model = ProdutoAgro
    template_name = 'Agricola/produto_agro_list.html'
    context_object_name = 'produtos_agro'
    empresa_field = 'prod_empr_agro'
    filial_field = 'prod_fili_agro'
    order_by_field = 'prod_nome_agro'

    def get_queryset(self):
        db_name = get_licenca_db_config(self.request) or 'default'
        qs = ProdutoAgro.objects.using(db_name).all()
        # filtros padrão empresa/filial
        empresa = getattr(self.request.user, 'empresa', None) or self.request.session.get('empresa_id', 1)
        filial = getattr(self.request.user, 'filial', None) or self.request.session.get('filial_id', 1)
        qs = qs.filter(prod_empr_agro=empresa, prod_fili_agro=filial)

        # filtros avançados
        q = (self.request.GET.get('q') or '').strip()
        codigo = (self.request.GET.get('codigo') or '').strip()
        nome = (self.request.GET.get('nome') or '').strip()
        categoria = (self.request.GET.get('categoria') or '').strip()

        if q:
            qs = qs.filter(Q(prod_codi_agro__icontains=q) | Q(prod_nome_agro__icontains=q))
        if codigo:
            qs = qs.filter(prod_codi_agro__icontains=codigo)
        if nome:
            qs = qs.filter(prod_nome_agro__icontains=nome)
        if categoria:
            qs = qs.filter(prod_cate_agro__iexact=categoria)

        return qs.order_by(self.order_by_field)[:100]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        db_name = get_licenca_db_config(self.request) or 'default'
        categorias = CategoriaProduto.objects.using(db_name).values_list('cate_nome', flat=True)
        context['categorias'] = categorias
        return context
