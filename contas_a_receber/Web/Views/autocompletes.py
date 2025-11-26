from django.http import JsonResponse
from django.db.models import Q
from core.utils import get_licenca_db_config
from CentrodeCustos.models import Centrodecustos



def autocomplete_cc(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    qs = Centrodecustos.objects.using(banco).filter(cecu_anal='A')
    if term:
        qs = qs.filter(Q(cecu_redu__icontains=term) | Q(cecu_nome__icontains=term))
    qs = qs.order_by('cecu_redu')[:30]
    data = [{'value': obj.cecu_redu, 'label': f"{obj.cecu_redu} - {obj.cecu_nome}"} for obj in qs]
    return JsonResponse({'results': data})

