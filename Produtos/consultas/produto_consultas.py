from django.db.models import Subquery, OuterRef, DecimalField, Value as V, Case, When, BigIntegerField, CharField, Q
from django.db.models.functions import Coalesce, Cast
from ..models import Produtos, SaldoProduto, Tabelaprecos

def listar_produtos(banco, empresa_id=None, filial_id=None, q=None, marca_nome=None, saldo_filter=None, limit=None):
    """
    Retorna queryset de produtos com saldos e preços anotados.
    Centraliza a lógica complexa de subqueries.
    """
    if not banco:
        return Produtos.objects.none()

    queryset = Produtos.objects.using(banco)

    # Subqueries
    saldo_qs = SaldoProduto.objects.using(banco).filter(
        produto_codigo=OuterRef('pk')
    )
    if empresa_id:
        saldo_qs = saldo_qs.filter(empresa=empresa_id)
    if filial_id:
        saldo_qs = saldo_qs.filter(filial=filial_id)

    saldo_subquery = Subquery(
        saldo_qs.values('saldo_estoque')[:1],
        output_field=DecimalField()
    )
    
    # Preços
    preco_base_qs = Tabelaprecos.objects.using(banco).filter(
        tabe_prod=OuterRef('prod_codi'),
        tabe_empr=OuterRef('prod_empr')
    ).exclude(
        tabe_entr__year__lt=1900
    ).exclude(
        tabe_entr__year__gt=2100
    )

    preco_vista_subquery = Subquery(
        preco_base_qs.values('tabe_avis')[:1],
        output_field=DecimalField()
    )

    preco_normal_subquery = Subquery(
        preco_base_qs.values('tabe_prco')[:1],
        output_field=DecimalField()
    )

    url_imagem = Subquery(
        Produtos.objects.using(banco).filter(
            prod_codi=OuterRef('prod_codi')
        ).values('prod_url')[:1],
        output_field=CharField()
    )

    # Annotate
    queryset = queryset.annotate(
        saldo_estoque=Coalesce(saldo_subquery, V(0), output_field=DecimalField()),
        prod_preco_vista=Coalesce(preco_vista_subquery, V(0), output_field=DecimalField()),
        prod_preco_normal=Coalesce(preco_normal_subquery, V(0), output_field=DecimalField()),
        prod_coba_str=Coalesce(Cast('prod_coba', CharField()), V('')),
        prod_url_img=Coalesce(url_imagem, V('')),
        prod_codi_int=Case(
            When(prod_codi__regex=r'^\d+$', then=Cast('prod_codi', BigIntegerField())),
            default=V(None),
            output_field=BigIntegerField()
        )
    )

    # Filtros
    if empresa_id:
        queryset = queryset.filter(prod_empr=empresa_id)

    if q:
        queryset = queryset.filter(
            Q(prod_nome__icontains=q) |
            Q(prod_coba_str__exact=q) |
            Q(prod_codi=q) | 
            Q(prod_codi__exact=q.lstrip("0"))
        )

    if marca_nome:
        if marca_nome == '__sem_marca__':
            queryset = queryset.filter(
                Q(prod_marc__isnull=True) | 
                Q(prod_marc__nome__isnull=True) |
                Q(prod_marc__nome='')
            )
        else:
            queryset = queryset.filter(prod_marc__nome=marca_nome)

    # Filtro de Saldo
    if saldo_filter:
        if saldo_filter == 'com':
            queryset = queryset.filter(saldo_estoque__gt=0)
        elif saldo_filter == 'sem':
            queryset = queryset.filter(saldo_estoque=0)
    
    queryset = queryset.order_by('prod_empr', 'prod_codi_int', 'prod_codi')

    if limit:
        queryset = queryset[:limit]

    return queryset

def buscar_produto_por_codigo(banco, empresa_id, codigo):
    """Busca um produto específico por empresa e código"""
    if not banco:
        return None
    
    return Produtos.objects.using(banco).filter(
        prod_empr=empresa_id,
        prod_codi=codigo
    ).first()
