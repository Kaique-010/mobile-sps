from django.views.generic import TemplateView
from requests import post
from Licencas.models import Empresas, Filiais
from core.middleware import get_licenca_slug
from django.http import JsonResponse
from core.utils import get_licenca_db_config
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Max, Q
from django.db import transaction
from datetime import datetime
import logging
from ..models import Caixageral, Movicaixa, TIPO_MOVIMENTO
from Pedidos.models import PedidoVenda, Itenspedidovenda
from ..services import CaixaService


logger = logging.getLogger(__name__)


class CaixaDashboardView(TemplateView):
    template_name = 'CaixaDiario/caixa_dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            slug_val = self.kwargs.get('slug') or get_licenca_slug()
        except Exception:
            slug_val = self.kwargs.get('slug')
        empresa = self.request.session.get('empresa_id') or self.request.headers.get('X-Empresa') or self.request.GET.get('empresa')
        filial = self.request.session.get('filial_id') or self.request.headers.get('X-Filial') or self.request.GET.get('filial')
        banco = get_licenca_db_config(self.request) or 'default'

        kpi = {'saldo_inicial': 0.0, 'entradas': 0.0, 'saidas': 0.0, 'saldo_atual': 0.0}
        caixas_data = []
        caixa_aberto_ctx = None
        mov_entradas = []
        mov_saidas = []
        try:
            if empresa and filial:
                qs = Caixageral.objects.using(banco).filter(caix_empr=empresa, caix_fili=filial, caix_aber='A').order_by('-caix_data', '-caix_hora')
                for c in qs:
                    caixas_data.append({
                        'caixa': c.caix_caix,
                        'data': str(c.caix_data),
                        'hora': str(c.caix_hora),
                        'operador': c.caix_oper,
                        'saldo_inicial': float(getattr(c, 'caix_valo', 0) or getattr(c, 'caix_sald_ini', 0) or 0),
                    })
                caixa_aberto = qs.first()
                if caixa_aberto:
                    caixa_aberto_ctx = {
                        'numero': int(caixa_aberto.caix_caix),
                        'data': str(caixa_aberto.caix_data),
                        'hora': str(caixa_aberto.caix_hora),
                        'operador': str(caixa_aberto.caix_oper),
                    }
                    saldo_inicial = float(getattr(caixa_aberto, 'caix_valo', 0) or getattr(caixa_aberto, 'caix_sald_ini', 0) or 0)
                    movs = Movicaixa.objects.using(banco).filter(
                        movi_empr=empresa,
                        movi_fili=filial,
                        movi_caix=caixa_aberto.caix_caix,
                        movi_data=caixa_aberto.caix_data
                    )
                    for m in movs.order_by('movi_ctrl'):
                        entr = float(getattr(m, 'movi_entr', 0) or 0)
                        said = float(getattr(m, 'movi_said', 0) or 0)
                        desc = str(getattr(m, 'movi_obse', '') or '')
                        ctrl = int(getattr(m, 'movi_ctrl', 0) or 0)
                        if entr > 0:
                            mov_entradas.append({'ctrl': ctrl, 'descricao': desc, 'valor': entr})
                        if said > 0:
                            mov_saidas.append({'ctrl': ctrl, 'descricao': desc, 'valor': said})
                    entradas = float(movs.aggregate(Sum('movi_entr'))['movi_entr__sum'] or 0)
                    saidas = float(movs.aggregate(Sum('movi_said'))['movi_said__sum'] or 0)
                    kpi = {
                        'saldo_inicial': saldo_inicial,
                        'entradas': entradas,
                        'saidas': saidas,
                        'saldo_atual': float(saldo_inicial) + entradas - saidas,
                    }
        except Exception:
            pass

        ctx.update({
            'slug': slug_val,
            'filtros': {
                'empresa': empresa,
                'filial': filial,
            },
            'kpi': kpi,
            'caixas_abertos': caixas_data,
            'caixa_aberto': caixa_aberto_ctx,
            'mov_entradas': mov_entradas,
            'mov_saidas': mov_saidas,
        })
        return ctx

class CaixaGeralPageView(TemplateView):
    template_name = 'CaixaDiario/caixa_geral.html'
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            slug_val = self.kwargs.get('slug') or get_licenca_slug()
        except Exception:
            slug_val = self.kwargs.get('slug')
        empresa = self.request.session.get('empresa_id') or self.request.headers.get('X-Empresa') or self.request.GET.get('empresa')
        filial = self.request.session.get('filial_id') or self.request.headers.get('X-Filial') or self.request.GET.get('filial')
        banco = get_licenca_db_config(self.request) or 'default'
        caixa_aberto_ctx = None
        try:
            if empresa and filial:
                caixa_aberto = Caixageral.objects.using(banco).filter(
                    caix_empr=empresa,
                    caix_fili=filial,
                    caix_aber='A'
                ).order_by('-caix_data', '-caix_hora').first()
                if caixa_aberto:
                    caixa_aberto_ctx = {
                        'caixa': int(caixa_aberto.caix_caix),
                        'data': str(caixa_aberto.caix_data),
                        'hora': str(caixa_aberto.caix_hora),
                        'operador': str(caixa_aberto.caix_oper),
                    }
        except Exception:
            pass

        ctx.update({
            'slug': slug_val,
            'empresa': empresa,
            'filial': filial,
            'caixa_aberto': caixa_aberto_ctx,
        })
        return ctx

class CaixaAbaVendaPageView(TemplateView):
    template_name = 'CaixaDiario/aba_venda.html'
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            slug_val = self.kwargs.get('slug') or get_licenca_slug()
        except Exception:
            slug_val = self.kwargs.get('slug')
        empresa = self.request.session.get('empresa_id') or self.request.headers.get('X-Empresa') or self.request.GET.get('empresa')
        filial = self.request.session.get('filial_id') or self.request.headers.get('X-Filial') or self.request.GET.get('filial')
        banco = get_licenca_db_config(self.request) or 'default'
        caixa_aberto_ctx = None
        try:
            if empresa and filial:
                caixa_aberto = Caixageral.objects.using(banco).filter(
                    caix_empr=empresa,
                    caix_fili=filial,
                    caix_aber='A'
                ).order_by('-caix_data', '-caix_hora').first()
                if caixa_aberto:
                    caixa_aberto_ctx = {
                        'caixa': int(caixa_aberto.caix_caix),
                        'data': caixa_aberto.caix_data,
                        'hora': caixa_aberto.caix_hora,
                        'operador': str(caixa_aberto.caix_oper),
                    }
        except Exception:
            pass

        ctx.update({
            'slug': slug_val,
            'empresa': empresa,
            'filial': filial,
            'caixa_aberto': caixa_aberto_ctx,
        })
        return ctx

class CaixaAbaProdutosPageView(TemplateView):
    template_name = 'CaixaDiario/aba_produtos.html'
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            slug_val = self.kwargs.get('slug') or get_licenca_slug()
        except Exception:
            slug_val = self.kwargs.get('slug')
        empresa = self.request.session.get('empresa_id') or self.request.headers.get('X-Empresa') or self.request.GET.get('empresa')
        filial = self.request.session.get('filial_id') or self.request.headers.get('X-Filial') or self.request.GET.get('filial')
        numero_venda = self.request.GET.get('numero_venda') or ''
        ctx.update({'slug': slug_val, 'empresa': empresa, 'filial': filial, 'numero_venda': numero_venda})
        return ctx

class CaixaAbaProcessamentoPageView(TemplateView):
    template_name = 'CaixaDiario/aba_processamento.html'
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            slug_val = self.kwargs.get('slug') or get_licenca_slug()
        except Exception:
            slug_val = self.kwargs.get('slug')
        empresa = self.request.session.get('empresa_id') or self.request.headers.get('X-Empresa') or self.request.GET.get('empresa')
        filial = self.request.session.get('filial_id') or self.request.headers.get('X-Filial') or self.request.GET.get('filial')
        numero_venda = self.request.GET.get('numero_venda') or ''
        ctx.update({'slug': slug_val, 'empresa': empresa, 'filial': filial, 'numero_venda': numero_venda})
        return ctx


class CaixaAbaExtratoPageView(TemplateView):
    template_name = 'CaixaDiario/aba_extrato.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            slug_val = self.kwargs.get('slug') or get_licenca_slug()
        except Exception:
            slug_val = self.kwargs.get('slug')
        empresa = self.request.session.get('empresa_id') or self.request.headers.get('X-Empresa') or self.request.GET.get('empresa')
        filial = self.request.session.get('filial_id') or self.request.headers.get('X-Filial') or self.request.GET.get('filial')
        caixa = self.request.GET.get('caixa') or ''
        ctx.update({'slug': slug_val, 'empresa': empresa, 'filial': filial, 'caixa': caixa})
        return ctx

def autocomplete_clientes(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id', 1)
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    from Entidades.models import Entidades
    qs = Entidades.objects.using(banco).filter(
        enti_empr=str(empresa_id),
        enti_clie__isnull=False,
    ).filter(
        Q(enti_tipo_enti__icontains='CL') | Q(enti_tipo_enti__icontains='AM')
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
    qs = Entidades.objects.using(banco).filter(enti_empr=str(empresa_id), enti_tipo_enti__icontains='VE')
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
    qs = Produtos.objects.using(banco).filter(prod_empr=str(empresa_id))
    if term:
        if term.isdigit():
            qs = qs.filter(prod_codi__icontains=term)
        else:
            qs = qs.filter(prod_nome__icontains=term)
    qs = qs.order_by('prod_nome')[:20]
    data = [{'id': str(obj.prod_codi), 'text': f"{obj.prod_codi} - {obj.prod_nome}"} for obj in qs]
    return JsonResponse({'results': data})

@require_http_methods(["GET"])
def caixas_abertos(request, slug=None):
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
    filial_id = request.session.get('filial_id') or request.headers.get('X-Filial') or request.GET.get('filial')
    if not empresa_id or not filial_id:
        return JsonResponse({'detail': 'Empresa e Filial são obrigatórios'}, status=400)
    qs = Caixageral.objects.using(banco).filter(caix_empr=empresa_id, caix_fili=filial_id, caix_aber='A').order_by('-caix_data', '-caix_hora')
    data = [
        {
            'caixa': c.caix_caix,
            'data': str(c.caix_data),
            'hora': str(c.caix_hora),
            'operador': c.caix_oper,
            'saldo_inicial': float(c.caix_sald_ini) if hasattr(c, 'caix_sald_ini') else 0.0,
        }
        for c in qs
    ]
    return JsonResponse({'results': data})

@require_http_methods(["GET"])
def origens_caixa(request, slug=None):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        if 'Authorization' not in request.headers:
            return JsonResponse({'detail': 'Autenticação requerida'}, status=403)
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
    filial_id = request.session.get('filial_id') or request.headers.get('X-Filial') or request.GET.get('filial')
    if not empresa_id or not filial_id:
        return JsonResponse({'detail': 'Empresa e Filial são obrigatórios'}, status=400)

    termo = (request.GET.get('term') or request.GET.get('q') or '').strip()

    from Entidades.models import Entidades

    # Buscamos Entidades configuradas como CAIXA ('C') ou BANCO ('B')
    # Isso permite selecionar caixas novos que ainda não têm movimentação
    qs = Entidades.objects.using(banco).filter(
        enti_empr=empresa_id,
        enti_tien__in=['C', 'B']
    )

    if termo:
        if termo.isdigit():
            qs = qs.filter(enti_clie__icontains=termo)
        else:
            qs = qs.filter(enti_nome__icontains=termo)

    qs = qs.order_by('enti_nome')[:20]

    resultados = [
        {
            'id': int(obj.enti_clie),
            'text': f"{obj.enti_clie} - {obj.enti_nome}",
        }
        for obj in qs
    ]

    return JsonResponse({'results': resultados})

@require_http_methods(["GET"])
def proximo_caixa_numero(request, slug=None):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        if 'Authorization' not in request.headers:
            return JsonResponse({'detail': 'Autenticação requerida'}, status=403)
    banco = get_licenca_db_config(request) or 'default'
    empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
    filial_id = request.session.get('filial_id') or request.headers.get('X-Filial') or request.GET.get('filial')
    if not empresa_id or not filial_id:
        return JsonResponse({'detail': 'Empresa e Filial são obrigatórios'}, status=400)
    max_caix = Caixageral.objects.using(banco).filter(caix_empr=empresa_id, caix_fili=filial_id).aggregate(Max('caix_caix'))['caix_caix__max'] or 0
    return JsonResponse({'proximo': int(max_caix) + 1})

@require_http_methods(["GET"])
def caixa_resumo(request, slug=None):
    banco = get_licenca_db_config(request)
    empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
    filial_id = request.session.get('filial_id') or request.headers.get('X-Filial') or request.GET.get('filial')
    if not empresa_id or not filial_id:
        return JsonResponse({'detail': 'Empresa e Filial são obrigatórios'}, status=400)
    caixa = request.GET.get('caixa')
    qs = Caixageral.objects.using(banco).filter(caix_empr=empresa_id, caix_fili=filial_id, caix_aber='A')
    if caixa:
        qs = qs.filter(caix_caix=caixa)
    caixa_aberto = qs.order_by('-caix_data', '-caix_hora').first()
    if not caixa_aberto:
        return JsonResponse({'detail': 'Nenhum caixa aberto encontrado'}, status=404)
    data_ref = caixa_aberto.caix_data
    saldo_inicial = float(getattr(caixa_aberto, 'caix_valo', 0) or getattr(caixa_aberto, 'caix_sald_ini', 0) or 0)
    movs = Movicaixa.objects.using(banco).filter(
        movi_empr=empresa_id,
        movi_fili=filial_id,
        movi_caix=caixa_aberto.caix_caix,
        movi_data=data_ref
    )
    entradas = float(movs.aggregate(Sum('movi_entr'))['movi_entr__sum'] or 0)
    saidas = float(movs.aggregate(Sum('movi_said'))['movi_said__sum'] or 0)
    saldo_atual = float(saldo_inicial) + entradas - saidas
    qtd_movimentos = movs.count()
    tipos_map = {'1': 'DINHEIRO', '2': 'CHEQUE', '3': 'CARTÃO DE CREDITO', '4': 'CARTÃO DE DEBITO', '5': 'CREDIÁRIO', '6': 'PIX'}
    por_forma = []
    for row in movs.values('movi_tipo').annotate(total=Sum('movi_entr')).order_by('-total'):
        tipo = str(row.get('movi_tipo'))
        por_forma.append({
            'tipo': tipo,
            'descricao': tipos_map.get(tipo, tipo),
            'total': float(row.get('total') or 0)
        })
    total_vendas = movs.exclude(movi_nume_vend__isnull=True).values('movi_nume_vend').distinct().count()
    return JsonResponse({
        'caixa': int(caixa_aberto.caix_caix),
        'data': str(data_ref),
        'saldo_inicial': float(saldo_inicial),
        'entradas': entradas,
        'saidas': saidas,
        'saldo_atual': float(saldo_atual),
        'qtd_movimentos': int(qtd_movimentos),
        'total_vendas': int(total_vendas),
        'por_forma': por_forma
    })

@csrf_exempt
@require_http_methods(["POST"])
def venda_iniciar(request, slug=None):
    banco = get_licenca_db_config(request)
    empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
    filial_id = request.session.get('filial_id') or request.headers.get('X-Filial') or request.GET.get('filial')
    if not empresa_id or not filial_id:
        return JsonResponse({'Detalhe': 'Empresa e Filial são obrigatórios'}, status=400)
    data = request.POST or request.GET
    cliente = data.get('cliente') or request.headers.get('X-Cliente') or request.GET.get('cliente')
    vendedor = data.get('vendedor') or request.headers.get('X-Vendedor') or request.GET.get('vendedor')
    caixa = data.get('caixa') or request.headers.get('X-Caixa') or request.GET.get('caixa')
    if not all([cliente, caixa]):
        return JsonResponse({'Detalhes': 'Cliente e caixa são obrigatórios'}, status=400)
    vendedor_val = (str(vendedor).strip() if vendedor is not None else '')
    caixa_aberto = Caixageral.objects.using(banco).filter(caix_empr=empresa_id, caix_fili=filial_id, caix_caix=caixa, caix_aber='A').first()
    if not caixa_aberto:
        return JsonResponse({'Detalhe': 'Caixa não está aberto'}, status=400)
    with transaction.atomic(using=banco):
        ultimo_num_pedido = PedidoVenda.objects.using(banco).filter(pedi_empr=empresa_id, pedi_fili=filial_id).aggregate(Max('pedi_nume'))['pedi_nume__max'] or 0
        ultimo_num_movimento = Movicaixa.objects.using(banco).filter(movi_empr=empresa_id, movi_fili=filial_id).aggregate(Max('movi_nume_vend'))['movi_nume_vend__max'] or 0
        numero_venda = max(ultimo_num_pedido, ultimo_num_movimento) + 1
        pedido_existente = PedidoVenda.objects.using(banco).filter(
            pedi_empr=empresa_id,
            pedi_fili=filial_id,
            pedi_nume=numero_venda,
            pedi_forn=cliente,
            pedi_data=datetime.today().date(),
            pedi_stat='0',
        ).first()
        if pedido_existente:
            pedido_existente.pedi_forn = cliente
            if vendedor_val:
                pedido_existente.pedi_vend = vendedor_val
            pedido_existente.pedi_data = datetime.today().date()
            pedido_existente.pedi_hora = datetime.now().time()
            pedido_existente.save(using=banco)
        else:
            PedidoVenda.objects.using(banco).create(
                pedi_empr=empresa_id,
                pedi_fili=filial_id,
                pedi_nume=numero_venda,
                pedi_forn=cliente,
                pedi_vend=vendedor_val or '0',
                pedi_data=datetime.today().date(),
                pedi_stat='0',
            )
    return JsonResponse({
        'numero_venda': numero_venda,
        'cliente': cliente,
        'vendedor': vendedor_val or '0',
        'caixa': caixa,
        'Numero daVenda': numero_venda,
        'Cliente': cliente,
        'Vendedor': vendedor_val or '0',
        'Caixa': caixa
    })

@csrf_exempt
@require_http_methods(["POST"])
def venda_adicionar_item(request, slug=None):
    banco = get_licenca_db_config(request)
    empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
    filial_id = request.session.get('filial_id') or request.headers.get('X-Filial') or request.GET.get('filial')
    if not empresa_id or not filial_id:
        return JsonResponse({'Detalhe': 'Empresa e Filial são obrigatórios'}, status=400)
    data = request.POST or request.GET
    numero_venda = data.get('numero_venda')
    produto = data.get('produto')
    quantidade = data.get('quantidade')
    if not all([numero_venda, produto, quantidade]):
        return JsonResponse({'Detalhe': 'Número da venda, produto e quantidade são obrigatórios'}, status=400)
    try:
        quantidade_val = float(quantidade)
    except Exception:
        return JsonResponse({'Detalhe': 'Quantidade inválida'}, status=400)
    if quantidade_val <= 0:
        return JsonResponse({'Detalhe': 'Quantidade inválida'}, status=400)
    try:
        from Produtos.models import Tabelaprecos
        tp = Tabelaprecos.objects.using(banco).filter(
            tabe_empr=str(empresa_id),
            tabe_fili=str(filial_id),
            tabe_prod=str(produto),
        ).first()
        if not tp:
            return JsonResponse({'Detalhe': 'Preço de venda à vista não encontrado para o produto'}, status=400)
        price = tp.tabe_avis or tp.tabe_apra
        valor_unitario = float(price)
    except Exception:
        return JsonResponse({'Detalhe': 'Preço de venda à vista não encontrado para o produto'}, status=400)
    with transaction.atomic(using=banco):
        pedido = PedidoVenda.objects.using(banco).filter(pedi_empr=empresa_id, pedi_fili=filial_id, pedi_nume=numero_venda).first()
        if not pedido:
            return JsonResponse({'Detalhe': f'Pedido {numero_venda} não encontrado'}, status=400)
        valor_total = float(quantidade_val) * float(valor_unitario)
        item_existente = Itenspedidovenda.objects.using(banco).filter(iped_empr=empresa_id, iped_fili=filial_id, iped_pedi=str(numero_venda), iped_prod=produto).first()
        if item_existente:
            item_existente.iped_unit = valor_unitario
            item_existente.iped_quan = float(item_existente.iped_quan) + float(quantidade_val)
            item_existente.iped_tota = float(item_existente.iped_quan) * float(item_existente.iped_unit)
            item_existente.save(using=banco)
            item_obj = item_existente
        else:
            ultimo_item = Itenspedidovenda.objects.using(banco).filter(iped_empr=empresa_id, iped_fili=filial_id, iped_pedi=str(numero_venda)).aggregate(Max('iped_item'))['iped_item__max'] or 0
            item_obj = Itenspedidovenda.objects.using(banco).create(
                iped_empr=empresa_id,
                iped_fili=filial_id,
                iped_pedi=str(numero_venda),
                iped_item=ultimo_item + 1,
                iped_prod=produto,
                iped_quan=quantidade_val,
                iped_unit=valor_unitario,
                iped_tota=valor_total,
                iped_data=pedido.pedi_data,
                iped_forn=pedido.pedi_forn
            )
        total_pedido = Itenspedidovenda.objects.using(banco).filter(iped_empr=empresa_id, iped_fili=filial_id, iped_pedi=str(numero_venda)).aggregate(Sum('iped_tota'))['iped_tota__sum'] or 0
        pedido.pedi_tota = total_pedido
        pedido.save(using=banco)
    return JsonResponse({'numero_venda': numero_venda, 'produto': produto, 'quantidade': float(quantidade_val), 'valor_unitario': float(valor_unitario), 'valor_total': float(valor_total), 'total_pedido': float(total_pedido), 'status': 'Item adicionado com sucesso'})

@csrf_exempt
@require_http_methods(["POST"])
def venda_atualizar_item(request, slug=None):
    banco = get_licenca_db_config(request)
    empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
    filial_id = request.session.get('filial_id') or request.headers.get('X-Filial') or request.GET.get('filial')
    if not empresa_id or not filial_id:
        return JsonResponse({'Detalhe': 'Empresa e Filial são obrigatórios'}, status=400)
    data = request.POST or request.GET
    numero_venda = data.get('numero_venda')
    produto = data.get('produto')
    quantidade = data.get('quantidade')
    if not all([numero_venda, produto]):
        return JsonResponse({'Detalhe': 'Número da venda e produto são obrigatórios'}, status=400)
    try:
        from Produtos.models import Tabelaprecos
        tp = Tabelaprecos.objects.using(banco).filter(
            tabe_empr=str(empresa_id),
            tabe_fili=str(filial_id),
            tabe_prod=str(produto),
        ).first()
        if not tp:
            return JsonResponse({'Detalhe': 'Preço de venda à vista não encontrado para o produto'}, status=400)
        price = tp.tabe_avis or tp.tabe_apra
        valor_unitario = float(price)
    except Exception:
        return JsonResponse({'Detalhe': 'Preço de venda à vista não encontrado para o produto'}, status=400)
    with transaction.atomic(using=banco):
        item = Itenspedidovenda.objects.using(banco).filter(
            iped_empr=empresa_id, iped_fili=filial_id, iped_pedi=str(numero_venda), iped_prod=produto
        ).first()
        if not item:
            return JsonResponse({'detail': 'Item não encontrado'}, status=404)
        if quantidade is not None and quantidade != '':
            item.iped_quan = float(quantidade)
        item.iped_unit = float(valor_unitario)
        item.iped_tota = float(item.iped_quan) * float(item.iped_unit)
        item.save(using=banco)
        total_pedido = Itenspedidovenda.objects.using(banco).filter(
            iped_empr=empresa_id, iped_fili=filial_id, iped_pedi=str(numero_venda)
        ).aggregate(Sum('iped_tota'))['iped_tota__sum'] or 0
        pedido = PedidoVenda.objects.using(banco).filter(
            pedi_empr=empresa_id, pedi_fili=filial_id, pedi_nume=numero_venda
        ).first()
        if pedido:
            pedido.pedi_tota = total_pedido
            pedido.save(using=banco)
    return JsonResponse({
        'numero_venda': numero_venda,
        'produto': produto,
        'quantidade': float(item.iped_quan),
        'valor_unitario': float(item.iped_unit),
        'valor_total': float(item.iped_tota),
        'total_pedido': float(total_pedido),
        'status': 'Item atualizado com sucesso'
    })

@csrf_exempt
@require_http_methods(["POST"])
def venda_remover_item(request, slug=None):
    banco = get_licenca_db_config(request)
    empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
    filial_id = request.session.get('filial_id') or request.headers.get('X-Filial') or request.GET.get('filial')
    if not empresa_id or not filial_id:
        return JsonResponse({'detail': 'Empresa e Filial são obrigatórios'}, status=400)
    data = request.POST or request.GET
    numero_venda = data.get('numero_venda')
    produto = data.get('produto')
    if not all([numero_venda, produto]):
        return JsonResponse({'detail': 'Número da venda e produto são obrigatórios'}, status=400)
    with transaction.atomic(using=banco):
        deleted, _ = Itenspedidovenda.objects.using(banco).filter(
            iped_empr=empresa_id, iped_fili=filial_id, iped_pedi=str(numero_venda), iped_prod=produto
        ).delete()
        if not deleted:
            return JsonResponse({'detail': 'Item não encontrado'}, status=404)
        total_pedido = Itenspedidovenda.objects.using(banco).filter(
            iped_empr=empresa_id, iped_fili=filial_id, iped_pedi=str(numero_venda)
        ).aggregate(Sum('iped_tota'))['iped_tota__sum'] or 0
        pedido = PedidoVenda.objects.using(banco).filter(
            pedi_empr=empresa_id, pedi_fili=filial_id, pedi_nume=numero_venda
        ).first()
        if pedido:
            pedido.pedi_tota = total_pedido
            pedido.save(using=banco)
    return JsonResponse({'numero_venda': numero_venda, 'produto': produto, 'total_pedido': float(total_pedido), 'status': 'Item removido com sucesso'})

@csrf_exempt
@require_http_methods(["POST"])
def venda_processar_pagamento(request, slug=None):
    banco = get_licenca_db_config(request)
    empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
    filial_id = request.session.get('filial_id') or request.headers.get('X-Filial') or request.GET.get('filial')
    if not empresa_id or not filial_id:
        return JsonResponse({'detail': 'Empresa e Filial são obrigatórios'}, status=400)
    data = request.POST or request.GET
    cliente = data.get('cliente')
    vendedor = data.get('vendedor')
    numero_venda = data.get('numero_venda')
    forma_pagamento = data.get('forma_pagamento')
    movi_tipo = data.get('movi_tipo')
    valor = data.get('valor')
    valor_pago = data.get('valor_pago')
    troco = data.get('troco')
    parcelas = data.get('parcelas') or 1
    tipo_movimento = CaixaService.resolver_tipo_movimento(movi_tipo=movi_tipo, forma_pagamento=forma_pagamento)
    operador = request.headers.get('usuario_id') or request.headers.get('X-Usuario')

    try:
        logger.info(
            "WEB venda_processar_pagamento chamando CaixaService banco=%s empr=%s fili=%s venda=%s tipo=%s forma=%s parcelas=%s",
            banco,
            empresa_id,
            filial_id,
            numero_venda,
            tipo_movimento,
            forma_pagamento,
            parcelas,
        )
        movimento, _ = CaixaService.processar_pagamento_venda(
            banco=banco,
            empresa_id=empresa_id,
            filial_id=filial_id,
            numero_venda=numero_venda,
            valor=valor,
            cliente=cliente,
            vendedor=vendedor,
            forma_pagamento=forma_pagamento,
            movi_tipo=movi_tipo,
            valor_pago=valor_pago,
            troco=troco,
            parcelas=parcelas,
            operador=operador,
        )
    except Exception as e:
        return JsonResponse({'detail': str(e)}, status=400)

    return JsonResponse({
        'success': True,
        'movimento_id': movimento.movi_ctrl,
        'movi_tipo': tipo_movimento,
        'movi_tipo_movi': forma_pagamento,
        'descricao_tipo': dict(TIPO_MOVIMENTO).get(str(tipo_movimento)),
        'valor_pago': float(valor_pago or valor),
        'troco': movimento.movi_said,
        'parcelas': parcelas,
        'movi_entr': movimento.movi_entr,
        'movi_said': movimento.movi_said
    })

@csrf_exempt
@require_http_methods(["POST"])
def venda_finalizar(request, slug=None):
    banco = get_licenca_db_config(request)
    empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
    filial_id = request.session.get('filial_id') or request.headers.get('X-Filial') or request.GET.get('filial')
    if not empresa_id or not filial_id:
        return JsonResponse({'detail': 'Empresa e Filial são obrigatórios'}, status=400)
    data = request.POST or request.GET
    numero_venda = data.get('numero_venda')
    mov = Movicaixa.objects.using(banco).filter(movi_empr=empresa_id, movi_fili=filial_id, movi_nume_vend=numero_venda).first()
    if mov:
        numero_venda = mov.movi_nume_vend
    movimentos = Movicaixa.objects.using(banco).filter(movi_empr=empresa_id, movi_fili=filial_id, movi_nume_vend=numero_venda)
    total_itens = movimentos.filter(movi_tipo='1').aggregate(total=Sum('movi_entr'))['total'] or 0
    total_pagamentos = movimentos.exclude(movi_tipo='1').aggregate(total=Sum('movi_entr'))['total'] or 0
    pedido = PedidoVenda.objects.using(banco).filter(pedi_empr=empresa_id, pedi_fili=filial_id, pedi_nume=numero_venda).first()
    if pedido:
        pedido.pedi_stat = '1'
        pedido.save(using=banco)
    return JsonResponse({'numero_venda': numero_venda, 'total_itens': float(total_itens), 'total_pagamentos': float(total_pagamentos), 'status': 'Finalizada'})


@csrf_exempt
@require_http_methods(["POST"])
def venda_emitir(request, slug=None):
    """
    Emite cupom ou NFC-e de uma venda
    em formato texto (40 colunas)
    """
    # Configuração inicial
    banco = get_licenca_db_config(request)
    
    empresa_id = (
        request.session.get('empresa_id') 
        or request.headers.get('X-Empresa')
        or request.GET.get('empresa')
    )
    
    filial_id = (
        request.session.get('filial_id')
        or request.headers.get('X-Filial')
        or request.GET.get('filial')
    )
    
    
    # Validações iniciais
    if not empresa_id or not filial_id:
        return JsonResponse({
            'detail': 
                'Empresa e Filial obrigatórios'
        }, status=400)
    
    # Extrai parâmetros
    data = request.POST or request.GET
    numero_venda = data.get('numero_venda')
    tipo = (
        data.get('tipo') or 'cupom'
    ).lower()
    cpfcnpj = (
        data.get('cpfcnpj') or ''
    ).strip()
    
    if not numero_venda:
        return JsonResponse({
            'detail': 
                'Número da venda obrigatório'
        }, status=400)
    
    # Busca pedido
    pedido = PedidoVenda.objects.using(
        banco
    ).filter(
        pedi_empr=empresa_id,
        pedi_fili=filial_id,
        pedi_nume=numero_venda
    ).first()
    
    if not pedido:
        return JsonResponse({
            'detail': 'Pedido não encontrado'
        }, status=404)
    
    # Busca empresa para dados do cabeçalho
    filial = Filiais.objects.using(
        banco
    ).filter(
        empr_codi=empresa_id
    ).first()

    qs_venda_base = Movicaixa.objects.using(banco).filter(
        movi_empr=empresa_id,
        movi_fili=filial_id,
    ).filter(
        Q(movi_nume_vend=numero_venda) | Q(movi_obse__icontains=f"Venda {numero_venda}")
    )
    coo_numero = None
    if tipo == 'cupom':
        try:
            data_ref = qs_venda_base.values_list('movi_data', flat=True).first() or datetime.today().date()
            coo_existente = qs_venda_base.exclude(movi_coo__isnull=True).values_list('movi_coo', flat=True).first()
            if coo_existente is not None:
                coo_numero = int(coo_existente)
            else:
                max_coo = Movicaixa.objects.using(banco).filter(
                    movi_empr=empresa_id,
                    movi_fili=filial_id,
                    movi_data=data_ref,
                ).aggregate(Max('movi_coo'))['movi_coo__max'] or 0
                try:
                    coo_numero = int(max_coo) + 1
                except Exception:
                    coo_numero = 1
            qs_venda_base.filter(Q(movi_entr__gt=0) | Q(movi_said__gt=0)).update(
                movi_coo=coo_numero,
                movi_docu_fisc=None,
                movi_seri_nota=None,
                movi_nume_nota=None,
            )
        except Exception:
            pass
    
    # ------------------------------------------------------------
    # EMISSÃO NFC-e (Modelo 65)
    # ------------------------------------------------------------
    if tipo == 'nfce':
        try:
            from Notas_Fiscais.models import Nota
            from Notas_Fiscais.services.nota_service import NotaService
            from Notas_Fiscais.aplicacao.emissao_service import EmissaoService
            from Notas_Fiscais.builders.pedido import PedidoNFeBuilder
            from django.utils import timezone
            from series.models import Series
            
            
            series = Series.objects.using(banco).filter(seri_empr=empresa_id, seri_fili=filial_id, seri_nome='NC').first()
            
            # Verifica se já existe nota para este pedido
            nota = Nota.objects.using(banco).filter(
                empresa=empresa_id,
                filial=filial_id,
                modelo='65',
                pedido_origem=str(numero_venda)
            ).exclude(status__in=[101, 102, 301, 302]).first()
            
            if not nota:
                # Contexto para o builder
                
                serie_consumidor = getattr(series, 'seri_codi', None) or '1'
                try:
                    serie_consumidor_int = int(str(serie_consumidor).strip())
                    if 900 <= serie_consumidor_int <= 999:
                        serie_consumidor_int = 1
                    serie_consumidor = str(serie_consumidor_int)
                except Exception:
                    serie_consumidor = '1'
                context = {
                    "empresa": int(empresa_id),
                    "filial": int(filial_id),
                    "modelo": "65",
                    "serie": serie_consumidor,
                    "numero": 0,
                    "ambiente": int(getattr(filial, 'empr_ambi_nfec', 2) or 2),
                    "tipo_operacao": 1,
                    "finalidade": 1,
                }

                # Cria a nota a partir do pedido
                builder = PedidoNFeBuilder(pedido, database=banco, **context)
                dto_dict = builder.build()
                
                # Prepara dados para NotaService.criar
                # Mescla contexto com campos adicionais que o NotaService espera
                data_nota = context.copy()
                data_nota.update({
                    "natureza_operacao": "VENDA",
                    "destinatario": pedido.pedi_forn, # ID do cliente
                    "pedido_origem": str(numero_venda),
                    "data_emissao": timezone.now(),
                    "consumidor_final": 1,
                    "indicador_presencial": 1,
                })
                
                # Prepara itens
                itens_nota = []
                impostos_map = {}
                
                for index, item_dto in enumerate(dto_dict['itens']):
                    # Copia o DTO para não alterar o original
                    item_nota = item_dto.copy()
                    
                    # Remove 'impostos' se existir para não conflitar com o relacionamento
                    if 'impostos' in item_nota:
                        del item_nota['impostos']
                    
                    # Prepara o dicionário de impostos para NotaItemImposto
                    # Mapeia os nomes usados no DTO para os nomes do model NotaItemImposto
                    impostos_data = {}
                    
                    # Mapeamento de campos (DTO -> Model)
                    mapa_campos = {
                        'aliq_icms': 'icms_aliquota',
                        'base_icms': 'icms_base',
                        'valor_icms': 'icms_valor',
                        
                        'aliq_pis': 'pis_aliquota',
                        'base_pis': 'pis_base',
                        'valor_pis': 'pis_valor',
                        
                        'aliq_cofins': 'cofins_aliquota',
                        'base_cofins': 'cofins_base',
                        'valor_cofins': 'cofins_valor',
                        
                        'aliq_ipi': 'ipi_aliquota',
                        'base_ipi': 'ipi_base',
                        'valor_ipi': 'ipi_valor',
                    }
                    
                    for campo_dto, campo_model in mapa_campos.items():
                        if campo_dto in item_dto:
                             impostos_data[campo_model] = item_dto[campo_dto]
                             
                    if impostos_data:
                        impostos_map[index] = impostos_data

                    itens_nota.append(item_nota)
                
                nota = NotaService.criar(
                    data=data_nota,
                    itens=itens_nota,
                    impostos_map=impostos_map,
                    transporte=None,
                    empresa=empresa_id,
                    filial=filial_id,
                    database=banco
                )
            
            # Se já autorizada
            if nota.status == 100:
                try:
                    qs_venda_base.filter(Q(movi_entr__gt=0) | Q(movi_said__gt=0)).update(
                        movi_docu_fisc=65,
                        movi_seri_nota=str(getattr(nota, 'serie', '') or ''),
                        movi_nume_nota=getattr(nota, 'numero', None),
                        movi_coo=None,
                    )
                except Exception:
                    pass
                chave = nota.chave_acesso
                url = f"https://www.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx?p={chave}" # Placeholder RS
                return JsonResponse({
                    'ok': True,
                    'tipo': 'nfce',
                    'status': 'Autorizada',
                    'chave': chave,
                    'xml': nota.xml_autorizado,
                    'url_danfe': url,
                    'mensagem': 'Nota já autorizada.'
                })
            
            # Emite
            service = EmissaoService(slug, banco)
            resp = service.emitir(nota.id)
            
            if resp.get('status') == 100:
                try:
                    nota = Nota.objects.using(banco).filter(id=nota.id).first() or nota
                    qs_venda_base.filter(Q(movi_entr__gt=0) | Q(movi_said__gt=0)).update(
                        movi_docu_fisc=65,
                        movi_seri_nota=str(getattr(nota, 'serie', '') or ''),
                        movi_nume_nota=getattr(nota, 'numero', None),
                        movi_coo=None,
                    )
                except Exception:
                    pass
                chave = resp.get('chave')
                url = f"https://www.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx?p={chave}" # Placeholder RS
                return JsonResponse({
                    'ok': True,
                    'tipo': 'nfce',
                    'status': 'Autorizada',
                    'chave': chave,
                    'xml': resp.get('xml_protocolo') or resp.get('xml'),
                    'url_danfe': url,
                })
            else:
                return JsonResponse({
                    'ok': False,
                    'tipo': 'nfce',
                    'status': 'Rejeitada',
                    'motivo': resp.get('motivo'),
                    'erros': resp.get('erros')
                }, status=400)
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'detail': f'Erro na emissão NFC-e: {str(e)}'}, status=500)
    
    # Busca itens
    itens = list(
        Itenspedidovenda.objects.using(
            banco
        ).filter(
            iped_empr=empresa_id,
            iped_fili=filial_id,
            iped_pedi=str(numero_venda)
        ).values(
            'iped_item',
            'iped_prod',
            'iped_quan',
            'iped_unit',
            'iped_tota'
        )
    )
    try:
        from Produtos.models import Produtos
        cods = [str(i['iped_prod']) for i in itens]
        nomes_map = {
            str(r['prod_codi']): r['prod_nome']
            for r in Produtos.objects.using(banco)
            .filter(prod_empr=str(empresa_id), prod_codi__in=cods)
            .values('prod_codi', 'prod_nome')
        }
    except Exception:
        nomes_map = {}
    
    # Calcula total
    total_venda = sum(
        float(i['iped_tota'] or 0)
        for i in itens
    )
    
    # Busca pagamentos
    pagamentos_qs = Movicaixa.objects.using(
        banco
    ).filter(
        movi_empr=empresa_id,
        movi_fili=filial_id,
        movi_nume_vend=numero_venda
    )
    
    pagamentos = pagamentos_qs.values(
        'movi_tipo'
    ).annotate(
        total=Sum('movi_entr')
    ).order_by('-total')
    
    # Mapa de formas de pagamento
    formas_map = {
        '1': 'DINHEIRO',
        '2': 'CHEQUE',
        '3': 'CARTÃO DE CREDITO',
        '4': 'CARTÃO DE DEBITO',
        '5': 'CREDIÁRIO',
        '6': 'PIX'
    }
    
    # Funções auxiliares
    def centralizar(texto, largura=40):
        return texto.center(largura)
    
    def linha_separadora(largura=40):
        return '-' * largura
    
    # Inicia montagem do cupom
    linhas = []
    
    # Cabeçalho
    if filial:
        linhas.append(
            centralizar(
                filial.empr_nome or ''
            )
        )
        if filial.empr_docu:
            linhas.append(
                centralizar(
                    f"{filial.empr_docu}: {filial.empr_docu}"
                )
            )
        if filial.empr_ende:
            linhas.append(
                centralizar(
                    filial.empr_ende
                )
            )
    
    linhas.append(linha_separadora())
    
    # Tipo de documento
    tipo_doc = (
        'CUPOM FISCAL' if tipo == 'cupom'
        else 'NFC-e'
    )
    linhas.append(centralizar(tipo_doc))
    if tipo == 'cupom' and coo_numero:
        linhas.append(centralizar(f"COO: {int(coo_numero)}"))
    linhas.append(linha_separadora())
    
    # Dados da venda
    linhas.append(
        f"Pedido número: {numero_venda}"
    )
    try:
        from Entidades.models import Entidades
        cliente_obj = Entidades.objects.using(banco).filter(
            enti_clie=pedido.pedi_forn,
            enti_empr=empresa_id,
        ).first()
        cliente_nome = (getattr(cliente_obj, 'enti_nome', None) or '').strip()
    except Exception:
        cliente_nome = ''

    if cliente_nome:
        linhas.append(f"Cliente: {pedido.pedi_forn} - {cliente_nome}")
    else:
        linhas.append(f"Cliente: {pedido.pedi_forn}")
    
    if cpfcnpj:
        linhas.append(f"CPF/CNPJ: {cpfcnpj}")
    
    linhas.append(linha_separadora())
    
    # Cabeçalho dos itens
    linhas.append(
        f"{'Código':<8} {'Descrição':<15}"
    )
    linhas.append(
        f"{'Qtd':<8} {'Unitário':>10} "
        f"{'Total':>10}"
    )
    linhas.append(linha_separadora())
    
    # Itens
    for item in itens:
        codigo = str(item['iped_prod'])[:8]
        desc = nomes_map.get(str(item['iped_prod'])) or codigo
        
        linhas.append(
            f"{codigo:<8} {desc:<15}"
        )
        
        qtd = float(item['iped_quan'] or 0)
        unit = float(item['iped_unit'] or 0)
        total = float(item['iped_tota'] or 0)
        
        linhas.append(
            f"{qtd:<8.2f} "
            f"{unit:>10.2f} "
            f"{total:>10.2f}"
        )
    
    linhas.append(linha_separadora())
    
    # Totais
    linhas.append(
        f"Tot. Quantidade...: "
        f"{sum(float(i['iped_quan'] or 0) for i in itens):.2f}"
    )
    linhas.append(
        f"Tot. Produtos.....: "
        f"{total_venda:.2f}"
    )
    linhas.append(
        f"Tot. Desconto.....: 0,00"
    )
    linhas.append(
        f"Líquido Pedido....: "
        f"{total_venda:.2f}"
    )
    
    linhas.append(linha_separadora())
    
    # Formas de pagamento
    for pg in pagamentos:
        forma = formas_map.get(
            str(pg['movi_tipo']),
            'OUTROS'
        )
        valor = float(pg['total'] or 0)
        linhas.append(
            f"{forma} -> Valor:{valor:.2f}"
        )
    
    linhas.append(linha_separadora())
    
    # Rodapé
    if tipo == 'cupom':
        linhas.append('')
        linhas.append(
            centralizar("NÃO É DOCUMENTO FISCAL")
        )
        linhas.append(
            centralizar(
                "SOLICITE DOCUMENTO FISCAL"
            )
        )
    else:
        linhas.append(
            centralizar(
                "Documento Fiscal Eletrônico"
            )
        )
    
    linhas.append('')
    linhas.append(
        centralizar("Obrigado pela preferência")
    )
    
    # Junta todas as linhas
    cupom_texto = '\n'.join(linhas)
    
    # HTML para exibição (mantém formatação)
    html = (
        f"<html><head>"
        f"<meta charset='utf-8'>"
        f"<title>Emissão</title>"
        f"</head>"
        f"<body style='"
        f"font-family:monospace;"
        f"font-size:12px;"
        f"white-space:pre;"
        f"padding:20px'>"
        f"{cupom_texto}"
        f"</body></html>"
    )

    return JsonResponse({
        'ok': True,
        'tipo': tipo,
        'html': html,
        'texto': cupom_texto,
        'coo': int(coo_numero) if (tipo == 'cupom' and coo_numero) else None,
    })

@require_http_methods(["GET"])
def venda_status(request, slug=None):
    banco = get_licenca_db_config(request)
    empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
    filial_id = request.session.get('filial_id') or request.headers.get('X-Filial') or request.GET.get('filial')
    if not empresa_id or not filial_id:
        return JsonResponse({'detail': 'Empresa e Filial são obrigatórios'}, status=400)
    numero_venda = request.GET.get('numero_venda')
    if not numero_venda:
        return JsonResponse({'detail': 'Número da venda é obrigatório'}, status=400)
    pedido = PedidoVenda.objects.using(banco).filter(
        pedi_empr=empresa_id,
        pedi_fili=filial_id,
        pedi_nume=numero_venda
    ).first()
    total_pedido = Itenspedidovenda.objects.using(banco).filter(
        iped_empr=empresa_id,
        iped_fili=filial_id,
        iped_pedi=str(numero_venda)
    ).aggregate(Sum('iped_tota'))['iped_tota__sum'] or 0
    total_pagamentos = Movicaixa.objects.using(banco).filter(
        movi_empr=empresa_id,
        movi_fili=filial_id,
        movi_nume_vend=numero_venda
    ).exclude(movi_tipo='1').aggregate(total=Sum('movi_entr'))['total'] or 0
    saldo = float(total_pedido) - float(total_pagamentos)
    return JsonResponse({
        'numero_venda': numero_venda,
        'exists': bool(pedido),
        'cliente': str(pedido.pedi_forn) if pedido else '',
        'vendedor': str(pedido.pedi_vend) if pedido else '',
        'total_venda': float(total_pedido),
        'total_pagamentos': float(total_pagamentos),
        'saldo_a_pagar': saldo
    })


@require_http_methods(["GET"])
def caixa_aberto(request, slug=None):
    banco = get_licenca_db_config(request)
    empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
    filial_id = request.session.get('filial_id') or request.headers.get('X-Filial') or request.GET.get('filial')
    if not empresa_id or not filial_id:
        return JsonResponse({'detail': 'Empresa e Filial são obrigatórios'}, status=400)
    s = Caixageral.objects.using(banco).filter(caix_empr=empresa_id, caix_fili=filial_id, caix_aber='A').order_by('-caix_data', '-caix_hora')
    data = [
        {
            'caixa': c.caix_caix,
            'data': str(c.caix_data),
            'hora': str(c.caix_hora),
            'operador': c.caix_oper,
            'saldo_inicial': float(c.caix_sald_ini) if hasattr(c, 'caix_sald_ini') else 0.0,
        }
        for c in s
    ]
    return JsonResponse({'results': data})


@require_http_methods(["GET"])
def venda_extrato(request, slug=None):
    banco = get_licenca_db_config(request)
    empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
    filial_id = request.session.get('filial_id') or request.headers.get('X-Filial') or request.GET.get('filial')
    if not empresa_id or not filial_id:
        return JsonResponse({'detail': 'Empresa e Filial são obrigatórios'}, status=400)
    caixa = request.GET.get('caixa')
    data_str = request.GET.get('data') or request.GET.get('data_ref')
    vendedor = request.GET.get('vendedor') or request.GET.get('pedi_vend') or request.GET.get('movi_vend')
    forma = request.GET.get('forma') or request.GET.get('forma_pagamento') or request.GET.get('movi_tipo_movi') or request.GET.get('movi_tipo')
    data_ref = None
    if data_str:
        try:
            data_ref = datetime.strptime(data_str, '%Y-%m-%d').date()
        except Exception:
            data_ref = None
    movimentos = Movicaixa.objects.using(banco).filter(movi_empr=empresa_id, movi_fili=filial_id)
    if caixa:
        movimentos = movimentos.filter(movi_caix=caixa)
    if data_ref:
        movimentos = movimentos.filter(movi_data=data_ref)
    if vendedor:
        movimentos = movimentos.filter(movi_vend=str(vendedor))
    if forma:
        movimentos = movimentos.filter(Q(movi_tipo_movi=str(forma)) | Q(movi_tipo=str(forma)))
    movimentos = movimentos.exclude(movi_nume_vend__isnull=True)
    numeros = list(movimentos.values_list('movi_nume_vend', flat=True).distinct())
    resultados = []
    tipos_map = {
        '1': 'DINHEIRO',
        '2': 'CHEQUE',
        '3': 'CARTÃO DE CREDITO',
        '4': 'CARTÃO DE DEBITO',
        '5': 'CREDIÁRIO',
        '6': 'PIX',
    }
    for num in numeros:
        pedido = PedidoVenda.objects.using(banco).filter(pedi_empr=empresa_id, pedi_fili=filial_id, pedi_nume=num).first()
        cliente_codigo = str(pedido.pedi_forn) if pedido and pedido.pedi_forn else ''
        cliente_nome = ''
        if cliente_codigo:
            try:
                from Entidades.models import Entidades
                cliente_nome = Entidades.objects.using(banco).filter(
                    enti_empr=str(empresa_id),
                    enti_clie=cliente_codigo,
                ).values_list('enti_nome', flat=True).first() or ''
            except Exception:
                cliente_nome = ''
        cliente_display = f'{cliente_codigo} - {cliente_nome}' if cliente_nome else cliente_codigo
        itens_qs = Itenspedidovenda.objects.using(banco).filter(iped_empr=empresa_id, iped_fili=filial_id, iped_pedi=str(num))
        try:
            from Produtos.models import Produtos
            cods = list(itens_qs.values_list('iped_prod', flat=True))
            nomes_map = {
                str(r['prod_codi']): r['prod_nome']
                for r in Produtos.objects.using(banco)
                .filter(prod_empr=str(empresa_id), prod_codi__in=cods)
                .values('prod_codi', 'prod_nome')
            }
        except Exception:
            nomes_map = {}
        itens = []
        for it in itens_qs:
            itens.append({
                'produto': str(it.iped_prod),
                'descricao': nomes_map.get(str(it.iped_prod)) or str(it.iped_prod),
                'quantidade': float(it.iped_quan or 0),
                'unitario': float(it.iped_unit or 0),
                'total': float(it.iped_tota or 0),
            })
        total_venda = float(itens_qs.aggregate(Sum('iped_tota'))['iped_tota__sum'] or 0)
        movs_venda = movimentos.filter(movi_nume_vend=num)
        mov_first = movs_venda.first()
        data_movimento = str(mov_first.movi_data) if mov_first and getattr(mov_first, 'movi_data', None) else ''
        aggs_pg = movs_venda.aggregate(entr=Sum('movi_entr'), said=Sum('movi_said'))
        total_pagamentos_bruto = float(aggs_pg.get('entr') or 0)
        total_troco = float(aggs_pg.get('said') or 0)
        total_pagamentos = float(total_pagamentos_bruto) - float(total_troco)
        saldo = float(total_venda) - float(total_pagamentos)
        pagamentos = []
        for row in movs_venda.values('movi_tipo').annotate(entr=Sum('movi_entr'), said=Sum('movi_said')).order_by('-entr'):
            tipo = str(row.get('movi_tipo'))
            total = float(row.get('entr') or 0) - float(row.get('said') or 0)
            if not total:
                continue
            pagamentos.append({
                'tipo': tipo,
                'descricao': tipos_map.get(tipo, tipo),
                'total': total,
            })
        resultados.append({
            'numero_venda': int(num),
            'data': data_movimento or (str(pedido.pedi_data) if pedido and pedido.pedi_data else ''),
            'caixa': int(mov_first.movi_caix) if mov_first else None,
            'vendedor': str(pedido.pedi_vend) if pedido else '',
            'cliente': cliente_display,
            'cliente_codigo': cliente_codigo,
            'cliente_nome': cliente_nome,
            'total_venda': total_venda,
            'total_pagamentos_bruto': total_pagamentos_bruto,
            'troco': total_troco,
            'total_pagamentos': total_pagamentos,
            'saldo': saldo,
            'pagamentos': pagamentos,
            'itens': itens,
        })
    totais = []
    resumo_pg = movimentos.aggregate(entr=Sum('movi_entr'), said=Sum('movi_said'))
    resumo_bruto = float(resumo_pg.get('entr') or 0)
    resumo_troco = float(resumo_pg.get('said') or 0)
    resumo_liquido = float(resumo_bruto) - float(resumo_troco)
    for row in movimentos.values('movi_tipo').annotate(entr=Sum('movi_entr'), said=Sum('movi_said')).order_by('-entr'):
        t = str(row.get('movi_tipo'))
        total_entr = float(row.get('entr') or 0)
        total_troco = float(row.get('said') or 0)
        total_liquido = float(total_entr) - float(total_troco)
        if not total_entr and not total_troco:
            continue
        totais.append({
            'tipo': t,
            'descricao': tipos_map.get(t, t),
            'total': total_entr,
            'troco': total_troco,
            'liquido': total_liquido,
        })

    data_kpi = data_ref
    if not data_kpi and caixa:
        try:
            cx = Caixageral.objects.using(banco).filter(
                caix_empr=empresa_id,
                caix_fili=filial_id,
                caix_caix=caixa,
                caix_aber='A'
            ).order_by('-caix_data', '-caix_hora').first()
            if cx:
                data_kpi = cx.caix_data
        except Exception:
            data_kpi = None

    saldo_inicial = 0.0
    if caixa and data_kpi:
        try:
            cx_ref = Caixageral.objects.using(banco).filter(
                caix_empr=empresa_id,
                caix_fili=filial_id,
                caix_caix=caixa,
                caix_data=data_kpi,
            ).order_by('-caix_hora').first()
            if cx_ref:
                saldo_inicial = float(getattr(cx_ref, 'caix_valo', 0) or getattr(cx_ref, 'caix_sald_ini', 0) or 0)
        except Exception:
            saldo_inicial = 0.0

    entradas_caixa = 0.0
    saidas_caixa = 0.0
    saldo_atual = float(saldo_inicial)
    if caixa and data_kpi:
        movs_kpi = Movicaixa.objects.using(banco).filter(
            movi_empr=empresa_id,
            movi_fili=filial_id,
            movi_caix=caixa,
            movi_data=data_kpi,
        )
        aggs_kpi = movs_kpi.aggregate(entr=Sum('movi_entr'), said=Sum('movi_said'))
        entradas_caixa = float(aggs_kpi.get('entr') or 0)
        saidas_caixa = float(aggs_kpi.get('said') or 0)
        saldo_atual = float(saldo_inicial) + float(entradas_caixa) - float(saidas_caixa)
    return JsonResponse({
        'results': resultados,
        'totais': totais,
        'resumo': {
            'bruto': resumo_bruto,
            'troco': resumo_troco,
            'liquido': resumo_liquido,
        }
        ,
        'kpi': {
            'caixa': int(caixa) if caixa else None,
            'data': str(data_kpi) if data_kpi else '',
            'saldo_inicial': float(saldo_inicial),
            'entradas': float(entradas_caixa),
            'saidas': float(saidas_caixa),
            'saldo_atual': float(saldo_atual),
        }
    })

@require_http_methods(["GET"])
def caixa_fechado(request, slug=None):
    banco = get_licenca_db_config(request)
    empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
    filial_id = request.session.get('filial_id') or request.headers.get('X-Filial') or request.GET.get('filial')
    if not empresa_id or not filial_id:
        return JsonResponse({'detail': 'Empresa e Filial são obrigatórios'}, status=400)
    s = Caixageral.objects.using(banco).filter(caix_empr=empresa_id, caix_fili=filial_id, caix_aber='F').order_by('-caix_data', '-caix_hora')
    data = [
        {
            'caixa': c.caix_caix,
            'data': str(c.caix_data),
            'hora': str(c.caix_hora),
            'operador': c.caix_oper,
            'saldo_inicial': float(c.caix_sald_ini) if hasattr(c, 'caix_sald_ini') else 0.0,
            'saldo_final': float(c.caix_sald_fim) if hasattr(c, 'caix_sald_fim') else 0.0,
        }
        for c in s
    ]
    return JsonResponse({'results': data})  

@require_http_methods(["GET"])
def caixa_movimentos(request, slug=None):
    banco = get_licenca_db_config(request)
    empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
    filial_id = request.session.get('filial_id') or request.headers.get('X-Filial') or request.GET.get('filial')
    if not empresa_id or not filial_id:
        return JsonResponse({'detail': 'Empresa e Filial são obrigatórios'}, status=400)

    caixa = request.GET.get('caixa')
    data_str = request.GET.get('data') or request.GET.get('data_ref')
    data_ref = None
    if data_str:
        try:
            from datetime import datetime
            data_ref = datetime.strptime(data_str, '%Y-%m-%d').date()
        except Exception:
            data_ref = None

    if not caixa or not data_ref:
        try:
            cx = Caixageral.objects.using(banco).filter(
                caix_empr=empresa_id,
                caix_fili=filial_id,
                caix_aber='A'
            ).order_by('-caix_data', '-caix_hora').first()
            if cx:
                if not caixa:
                    caixa = cx.caix_caix
                if not data_ref:
                    data_ref = cx.caix_data
        except Exception:
            caixa = caixa
            data_ref = data_ref

    if not caixa or not data_ref:
        return JsonResponse({'caixa': None, 'data': '', 'results': []})

    qs = Movicaixa.objects.using(banco).filter(
        movi_empr=empresa_id,
        movi_fili=filial_id,
        movi_caix=caixa,
        movi_data=data_ref,
    ).order_by('movi_ctrl')

    results = []
    for m in qs:
        results.append({
            'ctrl': int(getattr(m, 'movi_ctrl', 0) or 0),
            'descricao': str(getattr(m, 'movi_obse', '') or ''),
            'entr': float(getattr(m, 'movi_entr', 0) or 0),
            'said': float(getattr(m, 'movi_said', 0) or 0),
        })
    return JsonResponse({'caixa': int(caixa), 'data': str(data_ref), 'results': results})

@csrf_exempt
@require_http_methods(["POST"])
def caixa_reabrir(request, slug=None):
    banco = get_licenca_db_config(request)
    empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
    filial_id = request.session.get('filial_id') or request.headers.get('X-Filial') or request.GET.get('filial')
    if not empresa_id or not filial_id:
        return JsonResponse({'detail': 'Empresa e Filial são obrigatórios'}, status=400)

    data = request.POST or request.GET
    if not data:
        try:
            import json
            data = json.loads((request.body or b'').decode('utf-8') or '{}') or {}
        except Exception:
            data = {}

    caixa = data.get('caixa') or data.get('caix_caix')
    data_str = data.get('data') or data.get('caix_data')
    if not caixa or not data_str:
        return JsonResponse({'detail': 'Caixa e data são obrigatórios'}, status=400)

    try:
        data_ref = datetime.strptime(str(data_str)[:10], '%Y-%m-%d').date()
    except Exception:
        return JsonResponse({'detail': 'Data inválida'}, status=400)

    caixa = int(caixa)

    outro_aberto = Caixageral.objects.using(banco).filter(
        caix_empr=empresa_id,
        caix_fili=filial_id,
        caix_aber='A',
    ).exclude(caix_caix=caixa, caix_data=data_ref).order_by('-caix_data', '-caix_hora').first()
    if outro_aberto:
        return JsonResponse({'detail': 'Já existe outro caixa aberto. Feche antes de reabrir.'}, status=409)

    cx = Caixageral.objects.using(banco).filter(
        caix_empr=empresa_id,
        caix_fili=filial_id,
        caix_caix=caixa,
        caix_data=data_ref,
    ).order_by('-caix_hora').first()
    if not cx:
        return JsonResponse({'detail': 'Caixa não encontrado para esta data'}, status=404)

    if getattr(cx, 'caix_aber', None) == 'A':
        return JsonResponse({'ok': True, 'status': 'ja_aberto', 'caixa': caixa, 'data': str(data_ref)})

    if getattr(cx, 'caix_aber', None) != 'F':
        return JsonResponse({'detail': 'Status do caixa inválido para reabertura'}, status=400)

    cx.caix_aber = 'A'
    try:
        if hasattr(cx, 'caix_fech_data'):
            cx.caix_fech_data = None
        if hasattr(cx, 'caix_fech_hora'):
            cx.caix_fech_hora = None
        if hasattr(cx, 'caix_obse_fech'):
            cx.caix_obse_fech = ''
    except Exception:
        pass
    cx.save(using=banco)
    return JsonResponse({'ok': True, 'status': 'reaberto', 'caixa': caixa, 'data': str(data_ref)})


@csrf_exempt
@require_http_methods(["POST"])
def caixa_fechar(request, slug=None):
    banco = get_licenca_db_config(request)
    empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
    filial_id = request.session.get('filial_id') or request.headers.get('X-Filial') or request.GET.get('filial')
    if not empresa_id or not filial_id:
        return JsonResponse({'detail': 'Empresa e Filial são obrigatórios'}, status=400)
    data = request.POST or request.GET
    observacao = (data.get('observacao') or '').strip()
    qs = Caixageral.objects.using(banco).filter(caix_empr=empresa_id, caix_fili=filial_id, caix_aber='A').order_by('-caix_data', '-caix_hora')
    caixa_aberto = qs.first()
    if not caixa_aberto:
        return JsonResponse({'detail': 'Nenhum caixa aberto encontrado'}, status=404)
    from django.db.models import Sum
    saldo_inicial = float(getattr(caixa_aberto, 'caix_valo', 0) or getattr(caixa_aberto, 'caix_sald_ini', 0) or 0)
    movs = Movicaixa.objects.using(banco).filter(
        movi_empr=empresa_id,
        movi_fili=filial_id,
        movi_caix=caixa_aberto.caix_caix,
        movi_data=caixa_aberto.caix_data
    )
    entradas = float(movs.aggregate(Sum('movi_entr'))['movi_entr__sum'] or 0)
    saidas = float(movs.aggregate(Sum('movi_said'))['movi_said__sum'] or 0)
    saldo_final = float(saldo_inicial) + entradas - saidas
    from datetime import datetime
    caixa_aberto.caix_aber = 'F'
    try:
        caixa_aberto.caix_fech_data = datetime.today().date()
        caixa_aberto.caix_fech_hora = datetime.now().time()
        caixa_aberto.caix_obse_fech = observacao
    except Exception:
        pass
    caixa_aberto.save(using=banco)
    return JsonResponse({
        'ok': True,
        'status': 'fechado',
        'observacao': observacao,
        'caixa': int(caixa_aberto.caix_caix),
        'saldo_inicial': float(saldo_inicial),
        'entradas': float(entradas),
        'saidas': float(saidas),
        'saldo_final': float(saldo_final),
        'message': 'Caixa fechado com sucesso'
    })
        
        
@csrf_exempt
@require_http_methods(["POST"])
def lancamento(request, slug=None):
    banco = get_licenca_db_config(request)
    empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
    filial_id = request.session.get('filial_id') or request.headers.get('X-Filial') or request.GET.get('filial')
    if not empresa_id or not filial_id:
        return JsonResponse({'detail': 'Empresa e Filial são obrigatórios'}, status=400)
    data = request.POST or request.GET
    tipo = data.get('tipo')
    if not tipo:
        return JsonResponse({'detail': 'Tipo é obrigatório'}, status=400)
    if tipo not in ['entrada', 'saida']:
        return JsonResponse({'detail': 'Tipo inválido'}, status=400)
    valor = data.get('valor')
    forma = (data.get('forma') or '').strip().lower()
    observacao = data.get('observacao') or ''
    if not valor:
        return JsonResponse({'detail': 'Valor é obrigatório'}, status=400)
    operador = request.headers.get('usuario_id') or request.headers.get('X-Usuario')
    cliente = data.get('cliente')
    vendedor = data.get('vendedor')
    titulo = data.get('titulo') or data.get('movi_titu')
    serie = data.get('serie') or data.get('movi_seri')
    parcelas = data.get('parcelas') or data.get('movi_parc') or 1

    try:
        mov, _ = CaixaService.criar_lancamento_caixa(
            banco=banco,
            empresa_id=empresa_id,
            filial_id=filial_id,
            tipo=tipo,
            valor=valor,
            forma=forma,
            observacao=observacao,
            operador=operador,
            cliente=cliente,
            vendedor=vendedor,
            titulo=titulo,
            serie=serie,
            parcelas=parcelas,
        )
    except Exception as e:
        return JsonResponse({'detail': str(e)}, status=400)

    return JsonResponse({
        'ok': True,
        'tipo': tipo,
        'valor': float(valor),
        'forma': str(mov.movi_tipo),
        'movi_ctrl': int(mov.movi_ctrl)
    })
