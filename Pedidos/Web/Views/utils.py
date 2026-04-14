from django.http import JsonResponse
from django.db.models import Q
from core.utils import get_licenca_db_config

def autocomplete_clientes(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id', 1)
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    from Entidades.models import Entidades
    qs = Entidades.objects.using(banco).filter(
        enti_empr=str(empresa_id),
        enti_clie__isnull=False,
    ).filter(
        Q(enti_tipo_enti__icontains='CL') | Q(enti_tipo_enti__icontains='AM')
    )
    if term:
        if term.isdigit():
            qs = qs.filter(enti_clie__icontains=term)
        else:
            qs = qs.filter(enti_nome__icontains=term)
    qs = qs.order_by('enti_nome')[:20]
    data = [{'id': str(obj.enti_clie), 'text': f"{obj.enti_clie} - {obj.enti_nome}"} for obj in qs]
    return JsonResponse({'results': data})

def autocomplete_vendedores(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id', 1)
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    from Entidades.models import Entidades
    qs = Entidades.objects.using(banco).filter(
        enti_empr=str(empresa_id),
        enti_tipo_enti__icontains='VE'
    )
    if term:
        if term.isdigit():
            qs = qs.filter(enti_clie__icontains=term)
        else:
            qs = qs.filter(enti_nome__icontains=term)
    qs = qs.order_by('enti_nome')[:20]
    data = [{'id': str(obj.enti_clie), 'text': f"{obj.enti_clie} - {obj.enti_nome}"} for obj in qs]
    return JsonResponse({'results': data})


def busca_entidades(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id', 1)
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    tipo = (request.GET.get('tipo') or '').strip().lower()
    limit_raw = (request.GET.get('limit') or '').strip()
    try:
        limit = int(limit_raw) if limit_raw else 200
    except Exception:
        limit = 200

    from Pedidos.services.buscas import BuscasEntidadesService

    if tipo in {'vendedor', 'vendedores', 've'}:
        qs = BuscasEntidadesService.buscar_vendedores(banco=banco, empresa_id=empresa_id, busca=term, limit=limit)
    elif tipo in {'cliente', 'clientes', 'cl'}:
        qs = BuscasEntidadesService.buscar_clientes(banco=banco, empresa_id=empresa_id, busca=term, limit=limit)
    else:
        qs = BuscasEntidadesService.buscar_entidades(banco=banco, empresa_id=empresa_id, busca=term, limit=limit)

    data = [{'id': str(obj.enti_clie), 'text': f"{obj.enti_clie} - {obj.enti_nome}"} for obj in qs]
    return JsonResponse({'results': data})

def autocomplete_produtos(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id', 1)
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    from Produtos.models import Produtos
    qs = Produtos.objects.using(banco).filter(
        prod_empr=str(empresa_id),
    )
    if term:
        if term.isdigit():
            qs = qs.filter(prod_codi__icontains=term)
        else:
            qs = qs.filter(prod_nome__icontains=term)
    qs = qs.order_by('prod_nome')[:20]
    data = [{'id': str(obj.prod_codi), 'text': f"{obj.prod_codi} - {obj.prod_nome}"} for obj in qs]
    return JsonResponse({'results': data})

def preco_produto(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id', 1)
    filial_id = request.session.get('filial_id', 1)
    prod_codi = (request.GET.get('prod_codi') or '').strip()
    tipo_financeiro = (request.GET.get('pedi_fina') or '').strip()
    if not prod_codi:
        return JsonResponse({'error': 'prod_codi obrigatório'}, status=400)
    try:
        from Produtos.models import Tabelaprecos
        qs = Tabelaprecos.objects.using(banco).filter(
            tabe_empr=str(empresa_id),
            tabe_fili=str(filial_id),
            tabe_prod=str(prod_codi)
        )
        tp = qs.first()
        if not tp:
            return JsonResponse({'unit_price': None, 'found': False})
        if tipo_financeiro == '0':
            price = tp.tabe_avis or tp.tabe_apra
        else:
            price = tp.tabe_apra or tp.tabe_avis
        try:
            unit_price = float(price or 0)
        except Exception:
            unit_price = 0.0
        return JsonResponse({'unit_price': unit_price, 'found': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def lotes_produto(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id', 1)
    filial_id = request.session.get('filial_id', 1)
    prod_codi = (request.GET.get('prod_codi') or request.GET.get('produto') or '').strip()
    if not prod_codi:
        return JsonResponse({'results': [], 'saldo_total': 0, 'saldo_lotes': 0, 'saldo_sem_lote': 0})
    try:
        from decimal import Decimal
        from django.db.models import Sum
        from Produtos.models import Lote, SaldoProduto

        lotes_qs = (
            Lote.objects.using(banco)
            .filter(lote_empr=int(empresa_id), lote_prod=str(prod_codi), lote_ativ=True)
            .order_by('lote_data_vali', 'lote_lote')
            .values('lote_lote', 'lote_sald', 'lote_data_fabr', 'lote_data_vali', 'lote_obse')[:200]
        )
        results = []
        saldo_lotes = Decimal('0')
        for row in lotes_qs:
            sald = Decimal(str(row.get('lote_sald') or 0))
            saldo_lotes += sald
            results.append({
                'lote_lote': int(row.get('lote_lote')),
                'lote_sald': float(sald),
                'lote_data_fabr': row.get('lote_data_fabr'),
                'lote_data_vali': row.get('lote_data_vali'),
                'lote_obse': row.get('lote_obse'),
            })

        sp = (
            SaldoProduto.objects.using(banco)
            .filter(produto_codigo_id=str(prod_codi), empresa=str(empresa_id), filial=str(filial_id))
            .first()
        )
        saldo_total = Decimal(str(getattr(sp, 'saldo_estoque', 0) or 0))
        saldo_sem_lote = saldo_total - saldo_lotes

        return JsonResponse({
            'results': results,
            'saldo_total': float(saldo_total),
            'saldo_lotes': float(saldo_lotes),
            'saldo_sem_lote': float(saldo_sem_lote),
        })
    except Exception:
        return JsonResponse({'results': [], 'saldo_total': 0, 'saldo_lotes': 0, 'saldo_sem_lote': 0})
