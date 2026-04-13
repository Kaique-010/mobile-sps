from django.db import transaction
from django.db.models import Subquery
from decimal import Decimal, InvalidOperation

from Produtos.models import Lote, SaldoProduto, Produtos


def _to_decimal(value, default: str = '0'):
    try:
        if value is None:
            return Decimal(default)
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        s = str(value).strip().replace(',', '.')
        if s == '':
            return Decimal(default)
        return Decimal(s)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)


def obter_saldos_atuais(*, banco: str, empresa, filial, apenas_com_saldo: bool = True, limit: int = 50):
    qs = SaldoProduto.objects.using(banco).select_related('produto_codigo').filter(
        empresa=str(empresa),
        filial=str(filial),
    )
    if apenas_com_saldo:
        qs = qs.exclude(saldo_estoque__isnull=True).exclude(saldo_estoque=0)

    total = qs.count()
    amostra = []
    for s in qs.order_by('produto_codigo')[: max(0, int(limit or 0))]:
        codigo = str(getattr(s, 'produto_codigo_id', '') or '')
        nome = None
        try:
            prod = getattr(s, 'produto_codigo', None)
            if prod is not None:
                nome = getattr(prod, 'prod_nome', None)
        except Exception:
            nome = None
        amostra.append(
            {
                'produto': codigo,
                'nome': nome,
                'saldo_atual': _to_decimal(getattr(s, 'saldo_estoque', 0) or 0),
            }
        )

    return {'total': total, 'amostra': amostra}


def zerar_estoque(*, banco: str, empresa, filial, batch_size: int = 500, limit_resultados: int | None = 2000):
    empresa_s = str(empresa)
    filial_s = str(filial)
    batch_size = max(1, int(batch_size or 500))
    limit_resultados = None if limit_resultados is None else max(0, int(limit_resultados))

    base = SaldoProduto.objects.using(banco).select_related('produto_codigo').filter(
        empresa=empresa_s,
        filial=filial_s,
    )

    resultados = []
    zerados = 0
    lotes_zerados = 0

    with transaction.atomic(using=banco):
        while True:
            lote = list(
                base.exclude(saldo_estoque__isnull=True)
                .exclude(saldo_estoque=0)
                .order_by('produto_codigo')[:batch_size]
            )
            if not lote:
                break

            ids = []
            for s in lote:
                codigo = str(getattr(s, 'produto_codigo_id', '') or '')
                nome = None
                try:
                    prod = getattr(s, 'produto_codigo', None)
                    if prod is not None:
                        nome = getattr(prod, 'prod_nome', None)
                except Exception:
                    nome = None

                saldo_anterior = _to_decimal(getattr(s, 'saldo_estoque', 0) or 0)
                if saldo_anterior == 0:
                    continue

                ids.append(getattr(s, 'produto_codigo_id', None))
                if limit_resultados is None or len(resultados) < limit_resultados:
                    resultados.append(
                        {
                            'produto': codigo,
                            'nome': nome,
                            'saldo_anterior': saldo_anterior,
                            'saldo_atual': Decimal('0'),
                        }
                    )

            if not ids:
                break

            atualizados = SaldoProduto.objects.using(banco).filter(
                empresa=empresa_s,
                filial=filial_s,
                produto_codigo_id__in=ids,
            ).update(saldo_estoque=Decimal('0'))
            zerados += int(atualizados or 0)

        try:
            empresa_i = int(empresa_s)
        except Exception:
            empresa_i = empresa

        try:
            produtos_sq = SaldoProduto.objects.using(banco).filter(
                empresa=empresa_s,
                filial=filial_s,
            ).values('produto_codigo_id')
            lotes_zerados = (
                Lote.objects.using(banco)
                .filter(
                    lote_empr=empresa_i,
                    lote_prod__in=Subquery(produtos_sq),
                )
                .exclude(lote_sald__isnull=True)
                .exclude(lote_sald=0)
                .update(lote_sald=Decimal('0'))
            )
            lotes_zerados = int(lotes_zerados or 0)
        except Exception:
            lotes_zerados = 0

    nomes = {}
    try:
        codigos = [r.get('produto') for r in resultados if r.get('produto')]
        if codigos:
            prods = Produtos.objects.using(banco).filter(prod_codi__in=codigos).values('prod_codi', 'prod_nome')
            nomes = {str(p.get('prod_codi')): p.get('prod_nome') for p in prods}
    except Exception:
        nomes = {}

    for r in resultados:
        if not r.get('nome'):
            r['nome'] = nomes.get(r.get('produto'))

    return {
        'empresa': empresa_s,
        'filial': filial_s,
        'zerados': zerados,
        'lotes_zerados': lotes_zerados,
        'itens': resultados,
    }
