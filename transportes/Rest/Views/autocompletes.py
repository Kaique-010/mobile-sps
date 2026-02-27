from django.http import JsonResponse
from django.db.models import Q
from core.utils import get_licenca_db_config
from Entidades.models import Entidades
from Produtos.models import Marca
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
