from django.views.generic import ListView
from django.db.models import Subquery, OuterRef, BigIntegerField
from django.db.models.functions import Cast
from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug
from Saidas_Estoque.models import SaidasEstoque


class SaidaListView(ListView):
    model = SaidasEstoque
    template_name = 'Saidas/saidas_listar.html'
    context_object_name = 'saidas'
    paginate_by = 50

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        from Entidades.models import Entidades
        from Produtos.models import Produtos

        qs = SaidasEstoque.objects.using(banco).all()

        entidade_nome = Subquery(
            Entidades.objects.using(banco)
            .filter(enti_clie=Cast(OuterRef('said_enti'), BigIntegerField()))
            .values('enti_nome')[:1]
        )
        produto_nome = Subquery(
            Produtos.objects.using(banco)
            .filter(prod_codi=OuterRef('said_prod'))
            .values('prod_nome')[:1]
        )
        qs = qs.annotate(entidade_nome=entidade_nome, produto_nome=produto_nome)
        return qs.order_by('-said_data', '-said_sequ')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug') or get_licenca_slug()
        return context
