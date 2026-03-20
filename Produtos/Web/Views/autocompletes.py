from django.http import JsonResponse
from django.db.models import Q
from core.utils import get_licenca_db_config, get_ncm_master_db

from CFOP.models import CFOP as CFOPModel, NCM_CFOP_DIF
from ...models import (
    GrupoProduto,
    SubgrupoProduto,
    FamiliaProduto,
    Marca,
    Ncm,
    UnidadeMedida,
)



def autocomplete_unidades(request, slug=None):
    banco = get_ncm_master_db(request)
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    qs = UnidadeMedida.objects.using(banco).all()
    if term:
        qs = qs.filter(Q(unid_codi__icontains=term) | Q(unid_desc__icontains=term))
    qs = qs.order_by('unid_desc')[:30]
    data = [{'value': obj.unid_codi, 'label': f"{obj.unid_codi} - {obj.unid_desc}"} for obj in qs]
    return JsonResponse({'results': data})

def autocomplete_grupos(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    qs = GrupoProduto.objects.using(banco).all()
    if term:
        qs = qs.filter(Q(descricao__icontains=term) | Q(codigo__icontains=term))
    qs = qs.order_by('descricao')[:30]
    data = [{'value': obj.codigo, 'label': f"{obj.codigo} - {obj.descricao}"} for obj in qs]
    return JsonResponse({'results': data})

def autocomplete_subgrupos(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    qs = SubgrupoProduto.objects.using(banco).all()
    if term:
        qs = qs.filter(Q(descricao__icontains=term) | Q(codigo__icontains=term))
    qs = qs.order_by('descricao')[:30]
    data = [{'value': obj.codigo, 'label': f"{obj.codigo} - {obj.descricao}"} for obj in qs]
    return JsonResponse({'results': data})


def autocomplete_familias(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    qs = FamiliaProduto.objects.using(banco).all()
    if term:
        qs = qs.filter(Q(descricao__icontains=term) | Q(codigo__icontains=term))
    qs = qs.order_by('descricao')[:30]
    data = [{'value': obj.codigo, 'label': f"{obj.codigo} - {obj.descricao}"} for obj in qs]
    return JsonResponse({'results': data})

def autocomplete_marcas(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    qs = Marca.objects.using(banco).all()
    if term:
        qs = qs.filter(Q(nome__icontains=term) | Q(codigo__icontains=term))
    qs = qs.order_by('nome')[:30]
    data = [{'value': obj.codigo, 'label': f"{obj.codigo} - {obj.nome}"} for obj in qs]
    return JsonResponse({'results': data})


def autocomplete_ncms(request, slug=None):
    banco_tenant = get_licenca_db_config(request) or "default"
    banco = get_ncm_master_db(banco_tenant)
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    qs = Ncm.objects.using(banco).all()
    if term:
        digits = ''.join(ch for ch in term if ch.isdigit())
        dotted = None
        if digits and len(digits) == 8:
            dotted = f"{digits[:4]}.{digits[4:6]}.{digits[6:]}"
        q = Q(ncm_codi__icontains=term) | Q(ncm_desc__icontains=term)
        if dotted:
            q = q | Q(ncm_codi__icontains=dotted)
        if digits and digits != term:
            q = q | Q(ncm_codi__icontains=digits)
        qs = qs.filter(q)
    qs = qs.order_by('ncm_codi')[:30]
    data = [{'value': obj.ncm_codi, 'label': f"{obj.ncm_codi} - {obj.ncm_desc}"} for obj in qs]
    return JsonResponse({'results': data})


def ncm_fiscal_padrao(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
    ncm_code = (request.GET.get('ncm') or '').strip()
    cfop_code = (request.GET.get('cfop') or '').strip()
    resp = {'ncm': ncm_code, 'empresa': empresa_id, 'aliquotas': {}, 'override': {}}
    if not ncm_code:
        return JsonResponse(resp)
    ncm_db = get_ncm_master_db(banco)
    raw = str(ncm_code).strip()
    digits = ''.join(ch for ch in raw if ch.isdigit())
    candidates = []
    for c in (raw, digits):
        c = (c or '').strip()
        if c and c not in candidates:
            candidates.append(c)
    if digits and len(digits) == 8:
        dotted = f"{digits[:4]}.{digits[4:6]}.{digits[6:]}"
        if dotted not in candidates:
            candidates.insert(1, dotted)
    ncm = None
    for code in candidates:
        ncm = Ncm.objects.using(ncm_db).filter(ncm_codi=code).first()
        if ncm:
            break
    if not ncm and digits:
        from django.db.models import F, Value
        from django.db.models.functions import Replace
        ncm = (
            Ncm.objects.using(ncm_db)
            .annotate(
                _ncm_norm=Replace(
                    Replace(F("ncm_codi"), Value("."), Value("")),
                    Value(" "),
                    Value(""),
                )
            )
            .filter(_ncm_norm=digits)
            .first()
        )
    if ncm:
        from Produtos.models import NcmFiscalPadrao as NcmFiscalPadraoModel
        qs = NcmFiscalPadraoModel.objects.using(banco).filter(nfiscalpadrao_ncm=ncm)
        if empresa_id:
            try:
                qs = qs.filter(nfiscalpadrao_empr=int(empresa_id))
            except Exception:
                qs = qs.filter(nfiscalpadrao_empr=empresa_id)
        aliq = qs.first()
        if aliq:
            resp['aliquotas'] = {
                'ipi': aliq.nfiscalpadrao_aliq_ipi,
                'pis': aliq.nfiscalpadrao_aliq_pis,
                'cofins': aliq.nfiscalpadrao_aliq_cofins,
                'cbs': aliq.nfiscalpadrao_aliq_cbs,
                'ibs': aliq.nfiscalpadrao_aliq_ibs,
            }
    if ncm and cfop_code:
        cfop = CFOPModel.objects.using(banco).filter(cfop_codi=cfop_code).first()
        if cfop and empresa_id:
            override = NCM_CFOP_DIF.objects.using(banco).filter(ncm=ncm, cfop=cfop, ncm_empr=int(empresa_id)).first()
            if override:
                resp['override'] = {
                    'ipi': override.ncm_ipi_dif,
                    'pis': override.ncm_pis_dif,
                    'cofins': override.ncm_cofins_dif,
                    'cbs': override.ncm_cbs_dif,
                    'ibs': override.ncm_ibs_dif,
                    'icms': override.ncm_icms_aliq_dif,
                    'st': override.ncm_st_aliq_dif,
                }
    return JsonResponse(resp)
