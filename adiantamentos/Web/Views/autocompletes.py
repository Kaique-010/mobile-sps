from django.http import JsonResponse
from django.db.models import Q
from core.utils import get_licenca_db_config
from Entidades.models import Entidades


def autocomplete_entidades(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id')
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()

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


def autocomplete_bancos(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id')
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()

    qs = Entidades.objects.using(banco).filter(
        enti_empr=str(empresa_id),
        enti_tien='B',
        enti_tipo_enti__isnull=False,
    )

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

