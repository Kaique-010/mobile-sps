from django.http import JsonResponse
import logging
from django.views.generic import TemplateView
from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug
logger = logging.getLogger(__name__)

def autocomplete_clientes(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id', 1)
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    from Entidades.models import Entidades
    qs = Entidades.objects.using(banco).filter(
        enti_empr=str(empresa_id),
        enti_tipo_enti__icontains='CL'
    )
    if term:
        if term.isdigit():
            qs = qs.filter(enti_clie__icontains=term)
        else:
            qs = qs.filter(enti_nome__icontains=term)
    qs = qs.order_by('enti_nome')[:20]
    data = [{'id': str(obj.enti_clie), 'text': f"{obj.enti_clie} - {obj.enti_nome}"} for obj in qs]
    return JsonResponse({'results': data})

def autocomplete_vendedores(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id', 1)
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    from Entidades.models import Entidades
    qs = Entidades.objects.using(banco).filter(
        enti_empr=str(empresa_id),
        enti_tipo_enti__icontains='VE'
    )
    if term:
        if term.isdigit():
            qs = qs.filter(enti_clie__icontains=term)
        else:
            qs = qs.filter(enti_nome__icontains=term)
    qs = qs.order_by('enti_nome')[:20]
    data = [{'id': str(obj.enti_clie), 'text': f"{obj.enti_clie} - {obj.enti_nome}"} for obj in qs]
    return JsonResponse({'results': data})

def autocomplete_produtos(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id', 1)
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    from Produtos.models import Produtos
    qs = Produtos.objects.using(banco).filter(
        prod_empr=str(empresa_id),
    )
    if term:
        if term.isdigit():
            qs = qs.filter(prod_codi__icontains=term)
        else:
            qs = qs.filter(prod_nome__icontains=term)
    qs = qs.order_by('prod_nome')[:20]
    data = [{'id': str(obj.prod_codi), 'text': f"{obj.prod_codi} - {obj.prod_nome}"} for obj in qs]
    return JsonResponse({'results': data})

def preco_produto(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id', 1)
    filial_id = request.session.get('filial_id', 1)
    prod_codi = (request.GET.get('prod_codi') or '').strip()
    tipo_financeiro = (request.GET.get('pedi_fina') or '').strip()
    if not prod_codi:
        return JsonResponse({'error': 'prod_codi obrigatório'}, status=400)
    try:
        from Produtos.models import Tabelaprecos
        qs = Tabelaprecos.objects.using(banco).filter(
            tabe_empr=str(empresa_id),
            tabe_fili=str(filial_id),
            tabe_prod=str(prod_codi)
        )
        tp = qs.first()
        if not tp:
            return JsonResponse({'unit_price': None, 'found': False})
        if tipo_financeiro == '1':
            price = tp.tabe_avis or tp.tabe_prco or tp.tabe_praz
        else:
            price = tp.tabe_praz or tp.tabe_prco or tp.tabe_avis
        try:
            unit_price = float(price or 0)
        except Exception:
            unit_price = 0.0
        return JsonResponse({'unit_price': unit_price, 'found': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

class OsDashboardView(TemplateView):
    template_name = 'Os/os_dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            slug_val = self.kwargs.get('slug') or get_licenca_slug()
        except Exception:
            slug_val = self.kwargs.get('slug')
        empresa = self.request.session.get('empresa_id') or self.request.headers.get('X-Empresa') or self.request.GET.get('empresa')
        filial = self.request.session.get('filial_id') or self.request.headers.get('X-Filial') or self.request.GET.get('filial')
        data_inicial = self.request.GET.get('data_inicial')
        data_final = self.request.GET.get('data_final')
        vendedor = (self.request.GET.get('vendedor') or self.request.GET.get('nome_vendedor') or '').strip()
        cliente = (self.request.GET.get('cliente') or self.request.GET.get('nome_cliente') or '').strip()
        atendente = (self.request.GET.get('atendente') or '').strip()
        status_os = (self.request.GET.get('status_os') or '').strip()
        ctx.update({
            'slug': slug_val,
            'filtros': {
                'empresa': empresa,
                'filial': filial,
                'data_inicial': data_inicial,
                'data_final': data_final,
                'vendedor': vendedor,
                'cliente': cliente,
                'atendente': atendente,
                'status_os': status_os,
            }
        })
        return ctx

def autocomplete_atendentes(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    from ..models import OrdemServicoGeral
    qs = OrdemServicoGeral.objects.using(banco).all()
    if term:
        qs = qs.filter(atendente__icontains=term)
    rows = qs.values('atendente').order_by('atendente')[:20]
    data = [{'id': r['atendente'], 'text': r['atendente']} for r in rows if r.get('atendente')]
    return JsonResponse({'results': data})

def autocomplete_status_os(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    from ..models import OrdemServicoGeral
    qs = OrdemServicoGeral.objects.using(banco).all()
    if term:
        qs = qs.filter(status_os__icontains=term)
    rows = qs.values('status_os').order_by('status_os').distinct()[:50]
    data = [{'id': r['status_os'], 'text': r['status_os']} for r in rows if r.get('status_os')]
    return JsonResponse({'results': data})
