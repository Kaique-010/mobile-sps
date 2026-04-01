from django.http import JsonResponse
from django.views.decorators.http import require_GET
from core.utils import get_licenca_db_config
from contas_a_pagar.models import Bapatitulos
from contas_a_receber.models import Baretitulos


@require_GET
def adiantamento_usos(
    request,
    slug=None,
    *,
    adia_empr: int,
    adia_fili: int,
    adia_enti: int,
    adia_docu: int,
    adia_seri: str,
    adia_tipo: str,
):
    banco = get_licenca_db_config(request) or 'default'

    usos = []
    total = 0.0
    vinculo = 'adiantamento'

    if str(adia_tipo) == 'P':
        base = Bapatitulos.objects.using(banco).filter(
            bapa_empr=adia_empr,
            bapa_fili=adia_fili,
            bapa_forn=adia_enti,
            bapa_form__in=['A', 'P'],
        )
        qs = base.filter(bapa_id_adto=adia_docu).order_by('-bapa_dpag', '-bapa_sequ')
        if not qs.exists():
            vinculo = 'entidade'
            qs = base.order_by('-bapa_dpag', '-bapa_sequ')
        for b in qs[:200]:
            valor = float(b.bapa_valo_pago or b.bapa_sub_tota or 0)
            total += valor
            usos.append(
                {
                    'modulo': 'contas_a_pagar',
                    'titulo': str(b.bapa_titu),
                    'serie': str(b.bapa_seri or ''),
                    'parcela': str(b.bapa_parc or ''),
                    'data': str(b.bapa_dpag or ''),
                    'valor': valor,
                    'historico': str(b.bapa_hist or ''),
                }
            )
    elif str(adia_tipo) == 'R':
        base = Baretitulos.objects.using(banco).filter(
            bare_empr=adia_empr,
            bare_fili=adia_fili,
            bare_clie=adia_enti,
            bare_form__in=['A', 'P'],
        )
        qs = base.filter(bare_id_adto=adia_docu).order_by('-bare_dpag', '-bare_sequ')
        if not qs.exists():
            vinculo = 'entidade'
            qs = base.order_by('-bare_dpag', '-bare_sequ')
        for b in qs[:200]:
            valor = float(b.bare_valo_pago or b.bare_sub_tota or 0)
            total += valor
            usos.append(
                {
                    'modulo': 'contas_a_receber',
                    'titulo': str(b.bare_titu),
                    'serie': str(b.bare_seri or ''),
                    'parcela': str(b.bare_parc or ''),
                    'data': str(b.bare_dpag or ''),
                    'valor': valor,
                    'historico': str(b.bare_hist or ''),
                }
            )

    return JsonResponse(
        {
            'adiantamento': {
                'empresa': int(adia_empr),
                'filial': int(adia_fili),
                'entidade': int(adia_enti),
                'documento': int(adia_docu),
                'serie': str(adia_seri),
                'tipo': str(adia_tipo),
            },
            'total': total,
            'quantidade': len(usos),
            'vinculo': vinculo,
            'usos': usos,
        }
    )
