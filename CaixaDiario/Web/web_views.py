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
from ..models import Caixageral, Movicaixa
from Pedidos.models import PedidoVenda, Itenspedidovenda


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
        ctx.update({'slug': slug_val, 'empresa': empresa, 'filial': filial})
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
        ctx.update({'slug': slug_val, 'empresa': empresa, 'filial': filial})
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

    base_ids = list(
        Caixageral.objects.using(banco)
        .filter(caix_empr=empresa_id, caix_fili=filial_id)
        .values_list('caix_caix', flat=True)
        .distinct()
    )

    qs = Entidades.objects.using(banco).filter(
        enti_empr=str(empresa_id),
        enti_clie__in=base_ids or [-1],
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
    print("data_ref:", data_ref)
    saldo_inicial = float(getattr(caixa_aberto, 'caix_valo', 0) or getattr(caixa_aberto, 'caix_sald_ini', 0) or 0)
    movs = Movicaixa.objects.using(banco).filter(
        movi_empr=empresa_id,
        movi_fili=filial_id,
        movi_caix=caixa_aberto.caix_caix,
        movi_data=data_ref
    )
    entradas = float(movs.aggregate(Sum('movi_entr'))['movi_entr__sum'] or 0)
    print("entradas:", entradas)
    saidas = float(movs.aggregate(Sum('movi_said'))['movi_said__sum'] or 0)
    print("saidas:", saidas)
    saldo_atual = float(saldo_inicial) + entradas - saidas
    print("saldo_atual:", saldo_atual)
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
        return JsonResponse({'detail': 'Empresa e Filial são obrigatórios'}, status=400)
    data = request.POST or request.GET
    cliente = data.get('cliente') or request.headers.get('X-Cliente') or request.GET.get('cliente')
    vendedor = data.get('vendedor') or request.headers.get('X-Vendedor') or request.GET.get('vendedor')
    caixa = data.get('caixa') or request.headers.get('X-Caixa') or request.GET.get('caixa')
    if not all([cliente, vendedor, caixa]):
        return JsonResponse({'detail': 'Cliente, vendedor e caixa são obrigatórios'}, status=400)
    caixa_aberto = Caixageral.objects.using(banco).filter(caix_empr=empresa_id, caix_fili=filial_id, caix_caix=caixa, caix_aber='A').first()
    if not caixa_aberto:
        return JsonResponse({'detail': 'Caixa não está aberto'}, status=400)
    with transaction.atomic(using=banco):
        ultimo_num_pedido = PedidoVenda.objects.using(banco).filter(pedi_empr=empresa_id, pedi_fili=filial_id).aggregate(Max('pedi_nume'))['pedi_nume__max'] or 0
        ultimo_num_movimento = Movicaixa.objects.using(banco).filter(movi_empr=empresa_id, movi_fili=filial_id).aggregate(Max('movi_nume_vend'))['movi_nume_vend__max'] or 0
        numero_venda = max(ultimo_num_pedido, ultimo_num_movimento) + 1
        pedido_existente = PedidoVenda.objects.using(banco).filter(
            pedi_empr=empresa_id,
            pedi_fili=filial_id,
            pedi_nume=numero_venda,
            pedi_forn=cliente,
            pedi_vend=vendedor,
            pedi_data=datetime.today().date(),
            pedi_stat='0',
        ).first()
        if pedido_existente:
            pedido_existente.pedi_forn = cliente
            pedido_existente.pedi_vend = vendedor
            pedido_existente.pedi_data = datetime.today().date()
            pedido_existente.pedi_hora = datetime.now().time()
            pedido_existente.save(using=banco)
        else:
            PedidoVenda.objects.using(banco).create(
                pedi_empr=empresa_id,
                pedi_fili=filial_id,
                pedi_nume=numero_venda,
                pedi_forn=cliente,
                pedi_vend=vendedor,
                pedi_data=datetime.today().date(),
                pedi_stat='0',
            )
    return JsonResponse({'numero_venda': numero_venda, 'cliente': cliente, 'vendedor': vendedor, 'caixa': caixa})

@csrf_exempt
@require_http_methods(["POST"])
def venda_adicionar_item(request, slug=None):
    banco = get_licenca_db_config(request)
    empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
    filial_id = request.session.get('filial_id') or request.headers.get('X-Filial') or request.GET.get('filial')
    if not empresa_id or not filial_id:
        return JsonResponse({'detail': 'Empresa e Filial são obrigatórios'}, status=400)
    data = request.POST or request.GET
    numero_venda = data.get('numero_venda')
    produto = data.get('produto')
    quantidade = data.get('quantidade')
    valor_unitario = data.get('valor_unitario')
    if not all([numero_venda, produto, quantidade, valor_unitario]):
        return JsonResponse({'detail': 'Número da venda, produto, quantidade e valor unitário são obrigatórios'}, status=400)
    with transaction.atomic(using=banco):
        pedido = PedidoVenda.objects.using(banco).filter(pedi_empr=empresa_id, pedi_fili=filial_id, pedi_nume=numero_venda).first()
        if not pedido:
            return JsonResponse({'detail': f'Pedido {numero_venda} não encontrado'}, status=400)
        valor_total = float(quantidade) * float(valor_unitario)
        item_existente = Itenspedidovenda.objects.using(banco).filter(iped_empr=empresa_id, iped_fili=filial_id, iped_pedi=str(numero_venda), iped_prod=produto).first()
        if item_existente:
            item_existente.iped_quan = float(item_existente.iped_quan) + float(quantidade)
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
                iped_quan=quantidade,
                iped_unit=valor_unitario,
                iped_tota=valor_total,
                iped_data=pedido.pedi_data,
                iped_forn=pedido.pedi_forn
            )
        total_pedido = Itenspedidovenda.objects.using(banco).filter(iped_empr=empresa_id, iped_fili=filial_id, iped_pedi=str(numero_venda)).aggregate(Sum('iped_tota'))['iped_tota__sum'] or 0
        pedido.pedi_tota = total_pedido
        pedido.save(using=banco)
    return JsonResponse({'numero_venda': numero_venda, 'produto': produto, 'quantidade': float(quantidade), 'valor_unitario': float(valor_unitario), 'valor_total': float(valor_total), 'total_pedido': float(total_pedido), 'status': 'Item adicionado com sucesso'})

@csrf_exempt
@require_http_methods(["POST"])
def venda_atualizar_item(request, slug=None):
    banco = get_licenca_db_config(request)
    empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
    filial_id = request.session.get('filial_id') or request.headers.get('X-Filial') or request.GET.get('filial')
    if not empresa_id or not filial_id:
        return JsonResponse({'detail': 'Empresa e Filial são obrigatórios'}, status=400)
    data = request.POST or request.GET
    numero_venda = data.get('numero_venda')
    produto = data.get('produto')
    quantidade = data.get('quantidade')
    valor_unitario = data.get('valor_unitario')
    if not all([numero_venda, produto]):
        return JsonResponse({'detail': 'Número da venda e produto são obrigatórios'}, status=400)
    with transaction.atomic(using=banco):
        item = Itenspedidovenda.objects.using(banco).filter(
            iped_empr=empresa_id, iped_fili=filial_id, iped_pedi=str(numero_venda), iped_prod=produto
        ).first()
        if not item:
            return JsonResponse({'detail': 'Item não encontrado'}, status=404)
        if quantidade is not None and quantidade != '':
            item.iped_quan = float(quantidade)
        if valor_unitario is not None and valor_unitario != '':
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
    MAPEAMENTO_FORMAS = {'51': '3', '52': '4', '54': '1', '60': '6'}
    TIPO_MOVIMENTO = [('1', 'DINHEIRO'), ('2', 'CHEQUE'), ('3', 'CARTÃO DE CREDITO'), ('4', 'CARTÃO DE DEBITO'), ('5', 'CREDIÁRIO'), ('6', 'PIX')]
    tipo_movimento = None
    if movi_tipo:
        tipo_movimento = str(movi_tipo)
    elif forma_pagamento:
        tipo_movimento = MAPEAMENTO_FORMAS.get(str(forma_pagamento))
    if not all([numero_venda, valor]):
        return JsonResponse({'detail': 'Número da venda e valor são obrigatórios'}, status=400)
    if not tipo_movimento:
        return JsonResponse({'detail': 'Forma de pagamento inválida'}, status=400)
    tipos_validos = [choice[0] for choice in TIPO_MOVIMENTO]
    if tipo_movimento not in tipos_validos:
        return JsonResponse({'detail': f'Tipo de movimento inválido. Opções válidas: {tipos_validos}'}, status=400)
    caixa_aberto = Caixageral.objects.using(banco).filter(caix_empr=empresa_id, caix_fili=filial_id, caix_aber='A').first()
    if not caixa_aberto:
        return JsonResponse({'detail': 'Nenhum caixa aberto encontrado'}, status=400)
    ultimo_ctrl = Movicaixa.objects.using(banco).filter(movi_empr=empresa_id, movi_fili=filial_id, movi_data=caixa_aberto.caix_data).aggregate(Max('movi_ctrl'))['movi_ctrl__max'] or 0
    movimento = Movicaixa.objects.using(banco).create(
        movi_empr=empresa_id,
        movi_fili=filial_id,
        movi_caix=caixa_aberto.caix_caix,
        movi_nume_vend=numero_venda,
        movi_tipo=tipo_movimento,
        movi_tipo_movi=forma_pagamento,
        movi_vend=vendedor,
        movi_clie=cliente,
        movi_entr=valor_pago or valor,
        movi_said=troco if troco and float(troco) > 0 else 0,
        movi_obse=f"Venda {numero_venda}, Pagamento {dict(TIPO_MOVIMENTO).get(tipo_movimento)} - Parcelas: {parcelas}",
        movi_data=caixa_aberto.caix_data,
        movi_hora=datetime.now().time(),
        movi_ctrl=ultimo_ctrl + 1,
        movi_oper=request.headers.get('usuario_id') or request.headers.get('X-Usuario'),
        movi_parc=str(parcelas) if parcelas else '1'
    )
    return JsonResponse({'success': True, 'movimento_id': movimento.movi_ctrl, 'movi_tipo': tipo_movimento, 'movi_tipo_movi': forma_pagamento, 'descricao_tipo': dict(TIPO_MOVIMENTO).get(tipo_movimento), 'valor_pago': float(valor_pago or valor), 'troco': movimento.movi_said, 'parcelas': parcelas, 'movi_entr': movimento.movi_entr, 'movi_said': movimento.movi_said})

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
        pedido.pedi_stat = '0'
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
    ).exclude(movi_tipo='1')
    
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
    linhas.append(linha_separadora())
    
    # Dados da venda
    linhas.append(
        f"Pedido número: {numero_venda}"
    )
    linhas.append(
        f"Cliente: {pedido.pedi_forn}"
    )
    
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
        'texto': cupom_texto
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
        total_pagamentos = float(movs_venda.exclude(movi_tipo='1').aggregate(total=Sum('movi_entr'))['total'] or 0)
        saldo = float(total_venda) - total_pagamentos
        pagamentos = []
        for row in movs_venda.exclude(movi_tipo='1').values('movi_tipo').annotate(total=Sum('movi_entr')).order_by('-total'):
            tipo = str(row.get('movi_tipo'))
            pagamentos.append({
                'tipo': tipo,
                'descricao': tipos_map.get(tipo, tipo),
                'total': float(row.get('total') or 0),
            })
        resultados.append({
            'numero_venda': int(num),
            'data': str(pedido.pedi_data) if pedido and pedido.pedi_data else '',
            'caixa': int(movs_venda.first().movi_caix) if movs_venda.first() else None,
            'vendedor': str(pedido.pedi_vend) if pedido else '',
            'cliente': cliente_display,
            'cliente_codigo': cliente_codigo,
            'cliente_nome': cliente_nome,
            'total_venda': total_venda,
            'total_pagamentos': total_pagamentos,
            'saldo': saldo,
            'pagamentos': pagamentos,
            'itens': itens,
        })
    totais = []
    for row in movimentos.exclude(movi_tipo='1').values('movi_tipo').annotate(total=Sum('movi_entr')).order_by('-total'):
        t = str(row.get('movi_tipo'))
        totais.append({
            'tipo': t,
            'descricao': tipos_map.get(t, t),
            'total': float(row.get('total') or 0),
        })
    return JsonResponse({'results': resultados, 'totais': totais})

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
    try:
        valor = float(valor)
    except Exception:
        return JsonResponse({'detail': 'Valor inválido'}, status=400)
    if valor <= 0:
        return JsonResponse({'detail': 'Valor deve ser maior que zero'}, status=400)
    mapa = {
        'dinheiro': '1',
        'cheque': '2',
        'credito': '3',
        'crédito': '3',
        'debito': '4',
        'débito': '4',
        'crediario': '5',
        'crediário': '5',
        'pix': '6',
        '1': '1',
        '2': '2',
        '3': '3',
        '4': '4',
        '5': '5',
        '6': '6',
    }
    tipo_movimento = mapa.get(forma or 'dinheiro')
    tipos_validos = ['1', '2', '3', '4', '5', '6']
    if not tipo_movimento or tipo_movimento not in tipos_validos:
        return JsonResponse({'detail': 'Forma de pagamento inválida'}, status=400)
    caixa_aberto = Caixageral.objects.using(banco).filter(caix_empr=empresa_id, caix_fili=filial_id, caix_aber='A').first()
    if not caixa_aberto:
        return JsonResponse({'detail': 'Nenhum caixa aberto encontrado'}, status=400)
    ultimo_ctrl = Movicaixa.objects.using(banco).filter(movi_empr=empresa_id, movi_fili=filial_id, movi_data=caixa_aberto.caix_data).aggregate(Max('movi_ctrl'))['movi_ctrl__max'] or 0
    mov = Movicaixa.objects.using(banco).create(
        movi_empr=empresa_id,
        movi_fili=filial_id,
        movi_caix=caixa_aberto.caix_caix,
        movi_data=caixa_aberto.caix_data,
        movi_ctrl=ultimo_ctrl + 1,
        movi_tipo=tipo_movimento,
        movi_tipo_movi=tipo_movimento,
        movi_entr=valor if tipo == 'entrada' else 0,
        movi_said=valor if tipo == 'saida' else 0,
        movi_obse=observacao or f"Lancamento {tipo}",
        movi_hora=datetime.now().time(),
        movi_oper=request.headers.get('usuario_id') or request.headers.get('X-Usuario')
    )
    return JsonResponse({
        'ok': True,
        'tipo': tipo,
        'valor': float(valor),
        'forma': tipo_movimento,
        'movi_ctrl': int(mov.movi_ctrl)
    })
