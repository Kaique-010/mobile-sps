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
    promocional = str(request.GET.get('promocional', '0')).lower() in {'1', 'true', 'sim', 'yes'}
    opcoes = str(request.GET.get('opcoes', '0')).lower() in {'1', 'true', 'sim', 'yes'}
    modo = (request.GET.get('modo') or '').strip()
    if not prod_codi:
        return JsonResponse({'error': 'prod_codi obrigatório'}, status=400)
    try:
        tipo_financeiro = (request.GET.get('tipo') or request.GET.get('pedi_fina') or '0')

        if not modo:
            modo = 'avista' if str(tipo_financeiro) == '0' else 'prazo'

        from Produtos.servicos.preco_servico import buscar_preco_normal, obter_valor_preco_normal
        from Produtos.servicos.preco_promocional import buscar_preco_promocional, obter_valor_preco_promocional

        normal = buscar_preco_normal(
            banco=banco,
            tabe_empr=str(empresa_id),
            tabe_fili=str(filial_id),
            tabe_prod=str(prod_codi),
        )

        promo = None
        if promocional or opcoes:
            promo = buscar_preco_promocional(
                banco=banco,
                tabe_empr=str(empresa_id),
                tabe_fili=str(filial_id),
                tabe_prod=str(prod_codi),
            )

        valor_normal = obter_valor_preco_normal(preco=normal, modalidade=modo)
        valor_promo = obter_valor_preco_promocional(preco=promo, modalidade=modo) if promo else None

        if promocional and valor_promo is not None:
            unit_price = float(valor_promo or 0)
            source = 'promocional'
            found = True
        else:
            unit_price = float(valor_normal or 0)
            source = 'normal'
            found = valor_normal is not None

        payload = {'unit_price': unit_price, 'found': bool(found), 'source': source}
        if opcoes or promocional:
            payload['prices'] = {
                'normal': {
                    'avista': float(obter_valor_preco_normal(preco=normal, modalidade='avista') or 0) if normal else 0,
                    'prazo': float(obter_valor_preco_normal(preco=normal, modalidade='prazo') or 0) if normal else 0,
                },
                'promocional': {
                    'avista': float(obter_valor_preco_promocional(preco=promo, modalidade='avista') or 0) if promo else 0,
                    'prazo': float(obter_valor_preco_promocional(preco=promo, modalidade='prazo') or 0) if promo else 0,
                },
            }
        return JsonResponse(payload)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
