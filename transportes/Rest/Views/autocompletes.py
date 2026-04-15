from django.http import JsonResponse
from django.db.models import Q
from core.utils import get_licenca_db_config
from Entidades.models import Entidades
from transportes.models import Bombas, Veiculos
from Produtos.models import Marca
from Produtos.models import Produtos
from CentrodeCustos.models import Centrodecustos



def autocomplete_transportadoras(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id')
    
    if not empresa_id:
        return JsonResponse({'results': []})

    term = (request.GET.get('term') or request.GET.get('q') or '').strip()

    qs = Entidades.objects.using(banco).filter(enti_empr=empresa_id, enti_tien='T')

    if term:
        if term.isdigit():
            qs = qs.filter(enti_clie__icontains=term)
        else:
            qs = qs.filter(Q(enti_nome__icontains=term) | Q(enti_fant__icontains=term))

    qs = qs.order_by('enti_nome')[:20]
    data = [
        {
            'id': str(obj.enti_clie),
            'text': f"{obj.enti_clie} - {obj.enti_nome}",
        }
        for obj in qs
    ]
    return JsonResponse({'results': data})


def autocomplete_marcas(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()

    qs = Marca.objects.using(banco).all()

    if term:
        if term.isdigit():
            qs = qs.filter(nome__icontains=term)
        else:
            qs = qs.filter(Q(nome__icontains=term))

    qs = qs.order_by('nome')[:20]
    data = [
        {
            'id': str(obj.codigo),
            'text': f"{obj.codigo} - {obj.nome}",
        }
        for obj in qs
    ]
    return JsonResponse({'results': data})


def autocomplete_centrodecustos(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id')
    
    if not empresa_id:
        return JsonResponse({'results': []})

    term = (request.GET.get('term') or request.GET.get('q') or '').strip()

    qs = Centrodecustos.objects.using(banco).filter(cecu_empr=empresa_id, cecu_anal='A')

    if term:
        if term.isdigit():
            qs = qs.filter(cecu_redu__icontains=term)
        else:
            qs = qs.filter(Q(cecu_nome__icontains=term))

    qs = qs.order_by('cecu_nome')[:20]
    data = [
        {
            'id': str(obj.cecu_redu),
            'text': f"{obj.cecu_redu} - {obj.cecu_nome}",
        }
        for obj in qs
    ]
    return JsonResponse({'results': data})


def autocomplete_entidades(request, slug=None):
    """
    Busca geral de entidades (clientes, fornecedores, motoristas, etc.)
    Filtrada apenas pela empresa logada.
    """
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id')
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()

    # Filtra apenas pela empresa, sem restrição de tipo (enti_tien)
    qs = Entidades.objects.using(banco).filter(enti_empr=str(empresa_id))

    if term:
        if term.isdigit():
            qs = qs.filter(enti_clie__icontains=term)
        else:
            qs = qs.filter(Q(enti_nome__icontains=term) | Q(enti_fant__icontains=term))

    qs = qs.order_by('enti_nome')[:20]
    data = [
        {
            'id': str(obj.enti_clie),
            'text': f"{obj.enti_clie} - {obj.enti_nome}",
        }
        for obj in qs
    ]
    return JsonResponse({'results': data})

def get_entidade_detalhes(request, slug=None):
    """
    Retorna detalhes de uma entidade específica.
    Usado para preenchimento automático de campos (ex: cidade na rota do CTe).
    """
    banco = get_licenca_db_config(request) or 'default'
    entidade_id = request.GET.get('id')
    
    if not entidade_id:
        return JsonResponse({'error': 'ID não informado'}, status=400)
    
    entidade = Entidades.objects.using(banco).filter(enti_clie=entidade_id).first()
    
    if not entidade:
        return JsonResponse({'error': 'Entidade não encontrada'}, status=404)
        
    return JsonResponse({
        'id': entidade.enti_clie,
        'nome': entidade.enti_nome,
        'cidade_codigo': entidade.enti_codi_cida,
        'cidade_nome': entidade.enti_cida,
        'uf': entidade.enti_esta,
        'cnpj': entidade.enti_cnpj,
        'cpf': entidade.enti_cpf,
    })


def autocomplete_veiculos(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id')
    
    if not empresa_id:
        return JsonResponse({'results': []})

    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    transportadora_id = request.GET.get('transportadora_id')

    qs = Veiculos.objects.using(banco).filter(veic_empr=empresa_id)

    if transportadora_id:
        qs = qs.filter(veic_tran=transportadora_id)

    if term:
        # Busca por placa, marca ou frota, independente de ser dígito ou não
        qs = qs.filter(
            Q(veic_plac__icontains=term) | 
            Q(veic_marc__icontains=term) |
            Q(veic_frot__icontains=term)
        )

    qs = qs.order_by('veic_plac')[:20]
    data = [
        {
            'id': str(obj.veic_sequ),
            'text': f"{obj.veic_plac} - {obj.veic_marc or ''} {obj.veic_espe or ''}",
        }
        for obj in qs
    ]
    return JsonResponse({'results': data})


def autocomplete_bombas(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id')
    if not empresa_id:
        return JsonResponse({'results': []})

    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    qs = Bombas.objects.using(banco).filter(bomb_empr=empresa_id)

    if term:
        qs = qs.filter(Q(bomb_codi__icontains=term) | Q(bomb_desc__icontains=term))

    qs = qs.order_by('bomb_desc', 'bomb_codi')[:20]
    data = [
        {
            'id': str(obj.bomb_codi),
            'text': f"{obj.bomb_codi} - {obj.bomb_desc or ''}",
        }
        for obj in qs
    ]
    return JsonResponse({'results': data})


def autocomplete_combustiveis(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id')
    if not empresa_id:
        return JsonResponse({'results': []})

    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    qs = Produtos.objects.using(banco).filter(prod_empr=str(empresa_id))

    if term:
        qs = qs.filter(Q(prod_codi__icontains=term) | Q(prod_nome__icontains=term))

    qs = qs.order_by('prod_nome')[:20]
    data = [
        {
            'id': str(obj.prod_codi),
            'text': f"{obj.prod_codi} - {obj.prod_nome}",
        }
        for obj in qs
    ]
    return JsonResponse({'results': data})
