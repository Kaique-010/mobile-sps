from django.http import JsonResponse
from ...models import CFOPFiscal, CFOP
from core.utils import get_licenca_db_config
from Licencas.models import Filiais
from ...defaults_cfop import deduzir_defaults


def cfop_autocomplete(request, slug=None):
    q = (request.GET.get("q") or "").strip()
    banco = get_licenca_db_config(request) or "default"
    empresa_id = request.session.get("empresa_id") or request.session.get("filial_id", 1)

    # Busca em CFOPs cadastrados no sistema (tenant)
    qs_cfop = CFOP.objects.using(banco).all().order_by("cfop_codi")
    if empresa_id:
        try:
            qs_cfop = qs_cfop.filter(cfop_empr=int(empresa_id))
        except Exception:
            pass

    if q:
        if q.isdigit():
            qs_cfop = qs_cfop.filter(cfop_codi__startswith=q)
        else:
            qs_cfop = qs_cfop.filter(cfop_desc__icontains=q)

    # Fallback: consulta tabela fiscal (unmanaged) se não achar nada
    results = [
        {"value": c.cfop_codi, "label": f"{c.cfop_codi} - {c.cfop_desc}"}
        for c in qs_cfop[:30]
    ]
    if not results:
        results = []
        fiscal_aliases = []
        for alias in (banco, "default"):
            if alias and alias not in fiscal_aliases:
                fiscal_aliases.append(alias)

        for alias in fiscal_aliases:
            try:
                qs_fiscal = CFOPFiscal.objects.using(alias).all().order_by("cfop_codi")
                if q:
                    if q.isdigit():
                        qs_fiscal = qs_fiscal.filter(cfop_codi__startswith=q)
                    else:
                        qs_fiscal = qs_fiscal.filter(cfop_desc__icontains=q)
                results = [
                    {"value": c.cfop_codi, "label": f"{c.cfop_codi} - {c.cfop_desc}"}
                    for c in qs_fiscal[:30]
                ]
                if results:
                    break
            except Exception:
                continue

    return JsonResponse({
        "results": results
    })


def cfop_exigencias_ajax(request, slug):
    cfop = (request.GET.get("cfop") or "").strip()
    if not cfop:
        return JsonResponse({"error": "CFOP vazio"}, status=400)

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
