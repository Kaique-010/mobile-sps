from ..models import SaldoProduto
from datetime import date

def obter_saldo_produto(banco, empresa, filial, produto_codigo):
    if not banco:
        return None
    return SaldoProduto.objects.using(banco).filter(
        empresa=empresa,
        filial=filial,
        produto_codigo=produto_codigo
    ).first()


def obter_movimentacoes_produto(
    *,
    banco: str,
    empresa,
    filial,
    produto,
    data_inicio,
    data_fim,
    limit: int = 200,
):
    if not banco:
        return {
            'entradas': [],
            'saidas': [],
            'totais': {'entradas_qtd': 0.0, 'saidas_qtd': 0.0},
        }

    def to_date(v, fallback=None):
        if isinstance(v, date):
            return v
        s = (str(v or '')).strip()
        if not s:
            return fallback
        try:
            return date.fromisoformat(s)
        except Exception:
            return fallback

    di = to_date(data_inicio)
    df = to_date(data_fim)
    if not di or not df:
        hoje = date.today()
        di = di or hoje
        df = df or hoje

    try:
        emp = int(empresa)
    except Exception:
        emp = empresa
    try:
        fil = int(filial)
    except Exception:
        fil = filial

    produto_s = str(produto or '').strip()
    if not produto_s:
        return {
            'entradas': [],
            'saidas': [],
            'totais': {'entradas_qtd': 0.0, 'saidas_qtd': 0.0},
        }

    from django.db.models import BigIntegerField, OuterRef, Subquery
    from django.db.models.functions import Cast
    from Entidades.models import Entidades
    from Entradas_Estoque.models import EntradaEstoque
    from Saidas_Estoque.models import SaidasEstoque

    ent_nome_entrada = Subquery(
        Entidades.objects.using(banco)
        .filter(enti_clie=Cast(OuterRef('entr_enti'), BigIntegerField()))
        .values('enti_nome')[:1]
    )
    ent_nome_saida = Subquery(
        Entidades.objects.using(banco)
        .filter(enti_clie=Cast(OuterRef('said_enti'), BigIntegerField()))
        .values('enti_nome')[:1]
    )

    entradas_qs = (
        EntradaEstoque.objects.using(banco)
        .filter(
            entr_empr=emp,
            entr_fili=fil,
            entr_prod=produto_s,
            entr_data__range=(di, df),
        )
        .annotate(entidade_nome=ent_nome_entrada)
        .order_by('-entr_data', '-entr_sequ')
    )
    saidas_qs = (
        SaidasEstoque.objects.using(banco)
        .filter(
            said_empr=emp,
            said_fili=fil,
            said_prod=produto_s,
            said_data__range=(di, df),
        )
        .annotate(entidade_nome=ent_nome_saida)
        .order_by('-said_data', '-said_sequ')
    )

    entradas = list(
        entradas_qs.values(
            'entr_sequ',
            'entr_data',
            'entr_enti',
            'entidade_nome',
            'entr_quan',
            'entr_tota',
            'entr_lote_vend',
        )[: max(0, int(limit or 0))]
    )
    saidas = list(
        saidas_qs.values(
            'said_sequ',
            'said_data',
            'said_enti',
            'entidade_nome',
            'said_quan',
            'said_tota',
            'said_lote_vend',
        )[: max(0, int(limit or 0))]
    )

    def to_float(v):
        try:
            return float(v or 0)
        except Exception:
            return 0.0

    entradas_qtd = sum(to_float(r.get('entr_quan')) for r in entradas)
    saidas_qtd = sum(to_float(r.get('said_quan')) for r in saidas)

    return {
        'entradas': entradas,
        'saidas': saidas,
        'totais': {'entradas_qtd': entradas_qtd, 'saidas_qtd': saidas_qtd},
    }
