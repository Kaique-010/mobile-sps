# views.py
from django.http import JsonResponse
from django.views.generic import TemplateView
from ...models import CFOPFiscal, CFOP, MapaCFOP
from ...defaults_cfop import deduzir_defaults



def cfop_autocomplete(request, slug=None):
    q = request.GET.get("q", "").strip()

    qs = CFOPFiscal.objects.all()

    if q:
        qs = qs.filter(
            cfop_codi__icontains=q
        ) | qs.filter(
            cfop_desc__icontains=q
        )

    return JsonResponse({
        "results": [
            {"value": c.cfop_codi, "label": f"{c.cfop_codi} - {c.cfop_desc}"}
            for c in qs[:30]
        ]
    })


# CFOP/Web/Views/ajax.py  (ou junto das outras views)
from django.http import JsonResponse
from core.utils import get_licenca_db_config
from Licencas.models import Filiais
from ...defaults_cfop import deduzir_defaults


def cfop_exigencias_ajax(request, slug):
    cfop = request.GET.get("cfop", "").strip()
    if not cfop:
        return JsonResponse({"error": "CFOP vazio"}, status=400)

    # mesmo critério da CreateView
    banco = get_licenca_db_config(request) or "default"
    empresa_id = request.session.get("empresa_id") or request.session.get("filial_id", 1)
    filial_codi = request.session.get("filial_codi") or request.GET.get("filial_id")
    qs = Filiais.objects.using(banco).filter(empr_codi=empresa_id)
    if filial_codi:
        try:
            qs = qs.filter(empr_codi=int(filial_codi))
        except Exception:
            pass
    empresa = qs.first()
    regime = getattr(empresa, "empr_regi_trib", None)

    defaults = deduzir_defaults(cfop, regime)

    return JsonResponse(defaults)
