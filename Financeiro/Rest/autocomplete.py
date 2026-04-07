from django.db.models import Q
from django.http import JsonResponse
from CentrodeCustos.models import Centrodecustos
from core.utils import get_licenca_db_config
from Entidades.models import Entidades


def autocomplete_cc(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get("empresa_id")
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    qs = Centrodecustos.objects.using(banco).filter(cecu_anal='A')
    if empresa_id:
        qs = qs.filter(cecu_empr=int(empresa_id))
    if term:
        qs = qs.filter(Q(cecu_redu__icontains=term) | Q(cecu_nome__icontains=term))
    qs = qs.order_by('cecu_redu')[:30]
    data = [{'value': obj.cecu_redu, 'label': f"{obj.cecu_redu} - {obj.cecu_nome}"} for obj in qs]
    return JsonResponse({'results': data})


def autocomplete_bancos_caixas(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get("empresa_id")
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    qs = Entidades.objects.using(banco).filter(enti_tien__in=['B', 'C'])
    if empresa_id:
        qs = qs.filter(enti_empr=int(empresa_id))
    if term:
        if term.isdigit():
            qs = qs.filter(Q(enti_clie=int(term)) | Q(enti_nome__icontains=term))
        else:
            qs = qs.filter(Q(enti_nome__icontains=term))
    qs = qs.order_by('enti_nome')[:30]
    data = [{'value': obj.enti_clie, 'label': f"{obj.enti_clie} - {obj.enti_nome}"} for obj in qs]
    return JsonResponse({'results': data})
