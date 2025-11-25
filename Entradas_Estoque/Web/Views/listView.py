from django.views.generic import ListView
from django.http import JsonResponse
from django.db.models import Subquery, OuterRef, BigIntegerField
from django.db.models.functions import Cast
from urllib.parse import quote_plus

from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug
from ...models import EntradaEstoque


class EntradaListView(ListView):
    model = EntradaEstoque
    template_name = 'Entradas/entradas_listar.html'
    context_object_name = 'entradas'
    paginate_by = 20
    
    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        from Entidades.models import Entidades
        
        qs = EntradaEstoque.objects.using(banco).all()
        
        # Filtros
        entidade = (self.request.GET.get('entidade') or '').strip()


        if entidade:
            if entidade.isdigit():
                qs = qs.filter(entr_enti__icontains=entidade)
            else:
                entidades_ids = list(
                    Entidades.objects.using(banco)
                    .filter(enti_nome__icontains=entidade)
                    .values_list('enti_clie', flat=True)[:200]
                )
                if entidades_ids:
                    qs = qs.filter(entr_enti__in=entidades_ids) 
                else:
                    qs = qs.none()   # Nenhum resultado se não houver IDs

        # Anotar nomes (opcional)
        # entidade_nome = Subquery(
        #     Entidades.objects.using(banco)
        #     .filter(enti_clie=Cast(OuterRef('entr_enti'), BigIntegerField()))
        #     .values('enti_nome')[:1]
        # )
        # qs = qs.annotate(entidade_nome=entidade_nome)

        return qs.order_by('-entr_data', '-entr_sequ')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug') or get_licenca_slug()

        # Preservar filtros na paginação
        params = []
        for key in ['cliente', 'vendedor', 'status']:
            val = (self.request.GET.get(key) or '').strip()
            if val:
                params.append(f"{quote_plus(key)}={quote_plus(val)}")
        context['extra_query'] = "&".join(params)
        return context
