from django.http import JsonResponse
from django.db.models import Q
from core.utils import get_licenca_db_config
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
    banco = get_licenca_db_config(request) or 'default'
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
    banco = get_licenca_db_config(request) or 'default'
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    qs = Ncm.objects.using(banco).all()
    if term:
        qs = qs.filter(Q(ncm_codi__icontains=term) | Q(ncm_desc__icontains=term))
    qs = qs.order_by('ncm_codi')[:30]
    data = [{'value': obj.ncm_codi, 'label': f"{obj.ncm_codi} - {obj.ncm_desc}"} for obj in qs]
    return JsonResponse({'results': data})


def ncm_aliquotas(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
    ncm_code = (request.GET.get('ncm') or '').strip()
    cfop_code = (request.GET.get('cfop') or '').strip()
    resp = {'ncm': ncm_code, 'empresa': empresa_id, 'aliquotas': {}, 'override': {}}
    if not ncm_code:
        return JsonResponse(resp)
    ncm = Ncm.objects.using(banco).filter(ncm_codi=ncm_code).first()
    if ncm:
        from Produtos.models import NcmAliquota as NcmAliqModel
        qs = NcmAliqModel.objects.using(banco).filter(nali_ncm=ncm)
        if empresa_id:
            try:
                qs = qs.filter(nali_empr=int(empresa_id))
            except Exception:
                qs = qs.filter(nali_empr=empresa_id)
        aliq = qs.first()
        if aliq:
            resp['aliquotas'] = {
                'ipi': aliq.nali_aliq_ipi,
                'pis': aliq.nali_aliq_pis,
                'cofins': aliq.nali_aliq_cofins,
                'cbs': aliq.nali_aliq_cbs,
                'ibs': aliq.nali_aliq_ibs,
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
