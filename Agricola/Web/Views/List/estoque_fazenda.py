from .base import BaseListView
from Agricola.models import EstoqueFazenda, Fazenda, ProdutoAgro
from core.utils import get_licenca_db_config
from django.db.models import Q, Sum, F, DecimalField, ExpressionWrapper

class EstoqueFazendaListView(BaseListView):
    model = EstoqueFazenda
    template_name = 'Agricola/estoque_fazenda_list.html'
    context_object_name = 'estoques_fazenda'
    empresa_field = 'estq_empr'
    filial_field = 'estq_fili'
    order_by_field = 'id'

    def _build_queryset(self, *, db_name, apply_slice):
        qs = EstoqueFazenda.objects.using(db_name).all()

        empresa = getattr(self.request.user, 'empresa', None) or self.request.session.get('empresa_id', 1)
        filial = getattr(self.request.user, 'filial', None) or self.request.session.get('filial_id', 1)
        qs = qs.filter(estq_empr=empresa, estq_fili=filial)

        q = (self.request.GET.get('q') or '').strip()
        if q:
            prod_filters = Q(prod_nome_agro__icontains=q) | Q(prod_codi_agro__icontains=q)
            if q.isdigit():
                prod_filters |= Q(id=int(q))
            prod_ids = list(
                ProdutoAgro.objects.using(db_name).filter(
                    prod_empr_agro=empresa,
                    prod_fili_agro=filial,
                ).filter(prod_filters).values_list('id', flat=True)
            )

            faze_filters = Q(faze_nome__icontains=q)
            if q.isdigit():
                faze_filters |= Q(id=int(q))
            faze_ids = list(
                Fazenda.objects.using(db_name).filter(
                    faze_empr=empresa,
                    faze_fili=filial,
                ).filter(faze_filters).values_list('id', flat=True)
            )

            qs = qs.filter(
                Q(estq_prod__in=[str(i) for i in prod_ids]) |
                Q(estq_faze__in=[str(i) for i in faze_ids]) |
                Q(estq_prod__icontains=q) |
                Q(estq_faze__icontains=q)
            )

        if self.order_by_field:
            qs = qs.order_by(self.order_by_field)

        if apply_slice:
            return qs[:100]
        return qs

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        db_name = banco if isinstance(banco, str) else banco.get('db_name', 'default')
        self._qs_full = self._build_queryset(db_name=db_name, apply_slice=False)
        return self._build_queryset(db_name=db_name, apply_slice=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        banco = get_licenca_db_config(self.request) or 'default'
        db_name = banco if isinstance(banco, str) else banco.get('db_name', 'default')

        estoques = context['estoques_fazenda']
        
        faze_ids = set(e.estq_faze for e in estoques if e.estq_faze)
        prod_ids = set(e.estq_prod for e in estoques if e.estq_prod)

        # Fetch objects manually
        fazendas = {
            str(f.id): f 
            for f in Fazenda.objects.using(db_name).filter(id__in=faze_ids)
        }
        
        produtos = {
            str(p.id): p 
            for p in ProdutoAgro.objects.using(db_name).filter(id__in=prod_ids)
        }

        # Attach objects to each item for the template
        for estoque in estoques:
            faze_id = str(estoque.estq_faze)
            prod_id = str(estoque.estq_prod)
            
            estoque.faze_obj = fazendas.get(faze_id)
            estoque.prod_obj = produtos.get(prod_id)

        qs_full = getattr(self, '_qs_full', None) or self._build_queryset(db_name=db_name, apply_slice=False)
        qs_positivos = qs_full.filter(estq_quant__gt=0)

        total_produtos = qs_positivos.values('estq_prod').distinct().count()
        total_fazendas = qs_positivos.values('estq_faze').distinct().count()

        custo_expr = ExpressionWrapper(
            F('estq_quant') * F('estq_cust_medi'),
            output_field=DecimalField(max_digits=20, decimal_places=4)
        )
        total_valor_custo = qs_positivos.aggregate(total=Sum(custo_expr))['total'] or 0
        custo_por_fazenda = (total_valor_custo / total_fazendas) if total_fazendas else 0

        context['resumo'] = {
            'total_produtos': total_produtos,
            'total_valor_custo': total_valor_custo,
            'total_fazendas': total_fazendas,
            'custo_por_fazenda': custo_por_fazenda,
        }
            
        return context
