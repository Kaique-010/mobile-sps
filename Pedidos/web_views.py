from django.views.generic import CreateView, ListView, DetailView, UpdateView
import logging
from django.shortcuts import render, redirect
from urllib.parse import quote_plus
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from django.db.models import Q
from core.utils import get_licenca_db_config

logger = logging.getLogger(__name__)
from .models import PedidoVenda
from .forms import PedidoVendaForm
from .formssets import ItensPedidoFormSet
from .services.pedido_service import PedidoVendaService, proximo_pedido_numero
from django.db.models import Subquery, OuterRef, BigIntegerField, Sum, Count
from django.db.models.functions import Cast

# Endpoints de autocomplete simples (retornam {id, text})
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

# Endpoint para obter preço do produto conforme financeiro (à vista/prazo)
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

        # Mapear o tipo financeiro: '1' = à vista, demais = prazo
        if tipo_financeiro == '1':
            price = tp.tabe_avis or tp.tabe_prco or tp.tabe_praz
        else:
            price = tp.tabe_praz or tp.tabe_prco or tp.tabe_avis

        # Converter para float seguro
        try:
            unit_price = float(price or 0)
        except Exception:
            unit_price = 0.0

        logger.debug(
            "[Pedidos.preco_produto] prod_codi=%s pedi_fina=%s price_source=%s unit_price=%.2f",
            prod_codi,
            tipo_financeiro,
            ('avis' if tipo_financeiro == '1' else 'praz/prco fallback'),
            unit_price,
        )
        return JsonResponse({'unit_price': unit_price, 'found': True})
    except Exception as e:
        logger.exception("[Pedidos.preco_produto] Erro ao calcular preço: %s", e)
        return JsonResponse({'error': str(e)}, status=500)

class PedidoCreateView(CreateView):
    model = PedidoVenda
    form_class = PedidoVendaForm
    template_name = 'Pedidos/pedidocriar.html'


    def get_success_url(self):
        slug = self.kwargs.get('slug')
        return f"/web/{slug}/pedidos/" if slug else "/web/home/"

    def get_form_kwargs(self):
        """Passa parâmetros extras para o form"""
        kwargs = super().get_form_kwargs()
        kwargs['database'] = get_licenca_db_config(self.request) or 'default'
        kwargs['empresa_id'] = self.request.session.get('empresa_id', 1)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)
        
        if self.request.POST:
            context['formset'] = ItensPedidoFormSet(
                self.request.POST,
                form_kwargs={'database': banco, 'empresa_id': empresa_id}
            )
        else:
            context['formset'] = ItensPedidoFormSet(
                form_kwargs={'database': banco, 'empresa_id': empresa_id}
            )
        
        # Produtos para o template (usado no JavaScript para adicionar linhas)
        try:
            from Produtos.models import Produtos
            qs = Produtos.objects.using(banco).all()
            if empresa_id:
                qs = qs.filter(prod_empr=str(empresa_id))
            context['produtos'] = qs.order_by('prod_nome')[:500]
        except Exception as e:
            print(f"Erro ao carregar produtos: {e}")
            context['produtos'] = []
        
        context['slug'] = self.kwargs.get('slug')
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset_itens = context['formset']

        # Injetar empresa/filial da sessão
        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)
        banco = get_licenca_db_config(self.request) or 'default'
        
        logger.debug("[PedidoCreateView] Form valid=%s Formset valid=%s", form.is_valid(), formset_itens.is_valid())
        if form.is_valid() and formset_itens.is_valid():
            try:
                # Prepara dados do pedido
                pedido_data = form.cleaned_data.copy()
                pedido_data['pedi_empr'] = empresa_id
                pedido_data['pedi_fili'] = filial_id
                pedido_data['pedi_desc'] = pedido_data.get('pedi_desc', 0)
                pedido_data['pedi_topr'] = pedido_data.get('pedi_topr', 0)
                
                # Converte objetos Entidades para IDs
                if hasattr(pedido_data.get('pedi_forn'), 'enti_clie'):
                    pedido_data['pedi_forn'] = pedido_data['pedi_forn'].enti_clie
                if hasattr(pedido_data.get('pedi_vend'), 'enti_clie'):
                    pedido_data['pedi_vend'] = pedido_data['pedi_vend'].enti_clie
                
                logger.debug(
                    "[PedidoCreateView] Dados do pedido iniciais: pedi_forn=%s pedi_vend=%s pedi_desc=%s pedi_topr=%s",
                    getattr(pedido_data.get('pedi_forn'), 'enti_clie', pedido_data.get('pedi_forn')),
                    getattr(pedido_data.get('pedi_vend'), 'enti_clie', pedido_data.get('pedi_vend')),
                    pedido_data.get('pedi_desc'),
                    pedido_data.get('pedi_topr'),
                )

                # Extrai dados dos itens
                itens_data = []
                for item_form in formset_itens.forms:
                    if not item_form.cleaned_data:
                        continue
                    if item_form.cleaned_data.get('DELETE'):
                        continue
                    
                    item_data = item_form.cleaned_data.copy()
                    # Converte objeto Produto para ID
                    if hasattr(item_data.get('iped_prod'), 'prod_codi'):
                        item_data['iped_prod'] = item_data['iped_prod'].prod_codi
                    
                    logger.debug(
                        "[PedidoCreateView] Item: prod=%s quan=%s unit=%s desc=%s",
                        item_data.get('iped_prod'),
                        item_data.get('iped_quan', 1),
                        item_data.get('iped_unit', 0),
                        item_data.get('iped_desc', 0),
                    )
                    itens_data.append({
                        'iped_prod': item_data.get('iped_prod'),
                        'iped_quan': item_data.get('iped_quan', 1),
                        'iped_unit': item_data.get('iped_unit', 0),
                        'iped_desc': item_data.get('iped_desc', 0),
                    })
                
                if not itens_data:
                    messages.error(self.request, "O pedido precisa ter pelo menos um item.")
                    return self.form_invalid(form)
                
                # Cria o pedido usando o service (banco-aware e com cálculo de itens)
                logger.debug("[PedidoCreateView] Chamando service.create_pedido_venda com %d itens", len(itens_data))
                pedido = PedidoVendaService.create_pedido_venda(
                    banco,
                    pedido_data,
                    itens_data
                )
                logger.debug(
                    "[PedidoCreateView] Pedido criado pedi_nume=%s pedi_topr=%s pedi_desc=%s pedi_tota=%s",
                    getattr(pedido, 'pedi_nume', None), getattr(pedido, 'pedi_topr', None), getattr(pedido, 'pedi_desc', None), getattr(pedido, 'pedi_tota', None)
                )
                messages.success(self.request, f"Pedido {pedido.pedi_nume} criado com sucesso.")
                return redirect(self.get_success_url())

            except Exception as e:
                messages.error(self.request, f"Erro ao salvar pedido: {str(e)}")
                logger.exception("[PedidoCreateView] Falha ao salvar pedido: %s", e)
                import traceback
                traceback.print_exc()
                return self.form_invalid(form)
        else:
            # Mostra erros de validação
            if not form.is_valid():
                messages.error(self.request, f"Erros no formulário: {form.errors}")
            if not formset_itens.is_valid():
                messages.error(self.request, f"Erros nos itens: {formset_itens.errors}")
            return self.form_invalid(form)


class PedidosListView(ListView):
    model = PedidoVenda
    template_name = 'Pedidos/pedidos_listar.html'
    context_object_name = 'pedidos'
    paginate_by = 50
    
    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        from Entidades.models import Entidades
        
        qs = PedidoVenda.objects.using(banco).filter(
            pedi_empr=self.request.session.get('empresa_id', 1),
            pedi_fili=self.request.session.get('filiacao_id', 1),
        )
        
        # Filtros
        cliente_param = (self.request.GET.get('cliente') or '').strip()
        vendedor_param = (self.request.GET.get('vendedor') or '').strip()
        status = self.request.GET.get('status')

        if cliente_param:
            if cliente_param.isdigit():
                qs = qs.filter(pedi_forn__icontains=cliente_param)
            else:
                entidades_ids = list(
                    Entidades.objects.using(banco)
                    .filter(enti_nome__icontains=cliente_param)
                    .values_list('enti_clie', flat=True)[:200]
                )
                if entidades_ids:
                    qs = qs.filter(pedi_forn__in=entidades_ids)
                else:
                    qs = qs.none()

        if vendedor_param:
            if vendedor_param.isdigit():
                qs = qs.filter(pedi_vend__icontains=vendedor_param)
            else:
                vendedores_ids = list(
                    Entidades.objects.using(banco)
                    .filter(enti_nome__icontains=vendedor_param)
                    .values_list('enti_clie', flat=True)[:200]
                )
                if vendedores_ids:
                    qs = qs.filter(pedi_vend__in=vendedores_ids)
                else:
                    qs = qs.none()
                    
        if status not in (None, '', 'todos'):
            try:
                qs = qs.filter(pedi_stat=int(status))
            except (ValueError, TypeError):
                pass

        # Anotar nomes
        cliente_nome_subq = (
            Entidades.objects.using(banco)
            .filter(enti_clie=Cast(OuterRef('pedi_forn'), BigIntegerField()))
            .values('enti_nome')[:1]
        )
        vendedor_nome_subq = (
            Entidades.objects.using(banco)
            .filter(enti_clie=Cast(OuterRef('pedi_vend'), BigIntegerField()))
            .values('enti_nome')[:1]
        )
        qs = qs.annotate(
            cliente_nome=Subquery(cliente_nome_subq),
            vendedor_nome=Subquery(vendedor_nome_subq)
        ).order_by('-pedi_data', '-pedi_nume')

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')

        # Totais usando queryset base (sem annotations/order_by) para evitar GROUP BY
        banco = get_licenca_db_config(self.request) or 'default'
        from Entidades.models import Entidades
        qs_total = PedidoVenda.objects.using(banco).filter(
            pedi_empr=self.request.session.get('empresa_id', 1),
            pedi_fili=self.request.session.get('filiacao_id', 1),
        )

        cliente_param = (self.request.GET.get('cliente') or '').strip()
        vendedor_param = (self.request.GET.get('vendedor') or '').strip()
        status = self.request.GET.get('status')

        if cliente_param:
            if cliente_param.isdigit():
                qs_total = qs_total.filter(pedi_forn__icontains=cliente_param)
            else:
                entidades_ids = list(
                    Entidades.objects.using(banco)
                    .filter(enti_nome__icontains=cliente_param)
                    .values_list('enti_clie', flat=True)[:200]
                )
                if entidades_ids:
                    qs_total = qs_total.filter(pedi_forn__in=entidades_ids)
                else:
                    qs_total = qs_total.none()

        if vendedor_param:
            if vendedor_param.isdigit():
                qs_total = qs_total.filter(pedi_vend__icontains=vendedor_param)
            else:
                vendedores_ids = list(
                    Entidades.objects.using(banco)
                    .filter(enti_nome__icontains=vendedor_param)
                    .values_list('enti_clie', flat=True)[:200]
                )
                if vendedores_ids:
                    qs_total = qs_total.filter(pedi_vend__in=vendedores_ids)
                else:
                    qs_total = qs_total.none()

        if status not in (None, '', 'todos'):
            try:
                qs_total = qs_total.filter(pedi_stat=int(status))
            except (ValueError, TypeError):
                pass

        context['total_registros'] = qs_total.count()
        context['total_valor'] = qs_total.aggregate(Sum('pedi_tota'))['pedi_tota__sum'] or 0

        # Cards de resumo
        distintos_clientes = qs_total.values('pedi_forn').distinct().count()
        cards_resumo = [
            {'label': 'Total de Pedidos', 'qtd': context['total_registros'], 'valor': context['total_valor'], 'color': '#4a6cf7'},
            {'label': 'Clientes Distintos', 'qtd': distintos_clientes, 'valor': None, 'color': '#6ec1e4'},
        ]
        context['cards_resumo'] = cards_resumo

        # Cards por status
        STATUS_PEDIDOS = [
            {'value': 0, 'label': 'Pendente'},
            {'value': 1, 'label': 'Processando'},
            {'value': 2, 'label': 'Enviado'},
            {'value': 3, 'label': 'Concluído'},
            {'value': 4, 'label': 'Cancelado'},
        ]
        MAP_CORES_PED = {
            0: '#FFC107',
            1: '#007BFF',
            2: '#20C997',
            3: '#28A745',
            4: '#DC3545',
        }
        agg = list(qs_total.values('pedi_stat').annotate(qtd=Count('pedi_nume'), valor=Sum('pedi_tota')))
        by_status = {int(a['pedi_stat'] or 0): a for a in agg}
        cards_status = []
        for s in STATUS_PEDIDOS:
            k = int(s['value'])
            a = by_status.get(k, {'qtd': 0, 'valor': 0})
            cards_status.append({
                'status': k,
                'label': s['label'],
                'color': MAP_CORES_PED.get(k, '#6C757D'),
                'qtd': int(a.get('qtd') or 0),
                'valor': float(a.get('valor') or 0),
            })
        context['cards_por_status'] = cards_status

        # Preservar filtros na paginação
        params = []
        for key in ['cliente', 'vendedor', 'status']:
            val = (self.request.GET.get(key) or '').strip()
            if val:
                params.append(f"{quote_plus(key)}={quote_plus(val)}")
        context['extra_query'] = ("&" + "&".join(params)) if params else ""
        return context


class PedidoDetailView(DetailView):
    model = PedidoVenda
    template_name = 'Pedidos/pedido_detalhe.html'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        return PedidoVenda.objects.using(banco).all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')
        
        try:
            from Entidades.models import Entidades
            from Produtos.models import Produtos
            banco = get_licenca_db_config(self.request) or 'default'
            pedido = context.get('object')
            
            if pedido:
                cliente = Entidades.objects.using(banco).filter(
                    enti_clie=pedido.pedi_forn
                ).values('enti_nome').first()
                vendedor = Entidades.objects.using(banco).filter(
                    enti_clie=pedido.pedi_vend
                ).values('enti_nome').first()
                
                context['cliente_nome'] = cliente.get('enti_nome') if cliente else 'N/A'
                context['vendedor_nome'] = vendedor.get('enti_nome') if vendedor else 'N/A'

                # Itens detalhados com nome e foto do produto
                itens_qs = (
                    pedido.itens if hasattr(pedido, 'itens') else []
                )
                # Preferir consulta explícita usando o banco correto
                try:
                    itens_qs = Produtos.objects.none()  # placeholder para tipo
                    from .models import Itenspedidovenda
                    itens_qs = Itenspedidovenda.objects.using(banco).filter(
                        iped_empr=pedido.pedi_empr,
                        iped_fili=pedido.pedi_fili,
                        iped_pedi=str(pedido.pedi_nume)
                    ).order_by('iped_item')
                except Exception:
                    pass

                codigos = [i.iped_prod for i in itens_qs]
                produtos = Produtos.objects.using(banco).filter(prod_codi__in=codigos)
                prod_map = {p.prod_codi: {'nome': p.prod_nome, 'has_foto': bool(p.prod_foto)} for p in produtos}

                itens_detalhados = []
                for i in itens_qs:
                    meta = prod_map.get(i.iped_prod, {})
                    itens_detalhados.append({
                        'prod_codigo': i.iped_prod,
                        'prod_nome': meta.get('nome') or i.iped_prod,
                        'has_foto': bool(meta.get('has_foto')), 
                        'iped_quan': i.iped_quan,
                        'iped_unit': i.iped_unit,
                        'iped_tota': i.iped_tota,
                        'iped_item': getattr(i, 'iped_item', None),
                    })
                context['itens_detalhados'] = itens_detalhados
        except Exception as e:
            print(f"Erro ao carregar nomes: {e}")
            context['cliente_nome'] = 'N/A'
            context['vendedor_nome'] = 'N/A'
            
        return context


class PedidoPrintView(DetailView):
    model = PedidoVenda
    template_name = 'Pedidos/pedido_impressao.html'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        return PedidoVenda.objects.using(banco).all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')
        
        try:
            from Entidades.models import Entidades
            from Produtos.models import Produtos
            banco = get_licenca_db_config(self.request) or 'default'
            pedido = context.get('object')
            
            if pedido:
                cliente = Entidades.objects.using(banco).filter(
                    enti_clie=pedido.pedi_forn
                ).values('enti_nome').first()
                vendedor = Entidades.objects.using(banco).filter(
                    enti_clie=pedido.pedi_vend
                ).values('enti_nome').first()
                
                context['cliente_nome'] = cliente.get('enti_nome') if cliente else 'N/A'
                context['vendedor_nome'] = vendedor.get('enti_nome') if vendedor else 'N/A'

                # Itens detalhados com nome e foto para impressão
                try:
                    from .models import Itenspedidovenda
                    itens_qs = Itenspedidovenda.objects.using(banco).filter(
                        iped_empr=pedido.pedi_empr,
                        iped_fili=pedido.pedi_fili,
                        iped_pedi=str(pedido.pedi_nume)
                    ).order_by('iped_item')
                except Exception:
                    itens_qs = []

                codigos = [i.iped_prod for i in itens_qs]
                produtos = Produtos.objects.using(banco).filter(prod_codi__in=codigos)
                prod_map = {p.prod_codi: {'nome': p.prod_nome, 'has_foto': bool(p.prod_foto)} for p in produtos}

                itens_detalhados = []
                for i in itens_qs:
                    meta = prod_map.get(i.iped_prod, {})
                    itens_detalhados.append({
                        'prod_codigo': i.iped_prod,
                        'prod_nome': meta.get('nome') or i.iped_prod,
                        'has_foto': bool(meta.get('has_foto')),
                        'iped_quan': i.iped_quan,
                        'iped_unit': i.iped_unit,
                        'iped_tota': i.iped_tota,
                        'iped_item': getattr(i, 'iped_item', None),
                    })
                context['itens_detalhados'] = itens_detalhados
        except Exception as e:
            print(f"Erro ao carregar nomes: {e}")
            context['cliente_nome'] = 'N/A'
            context['vendedor_nome'] = 'N/A'
            
        return context


class PedidoUpdateView(UpdateView):
    model = PedidoVenda
    form_class = PedidoVendaForm
    template_name = 'Pedidos/pedidocriar.html'

    def get_success_url(self):
        slug = self.kwargs.get('slug')
        return f"/web/{slug}/pedidos/" if slug else "/web/home/"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['database'] = get_licenca_db_config(self.request) or 'default'
        kwargs['empresa_id'] = self.request.session.get('empresa_id', 1)
        return kwargs

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        return PedidoVenda.objects.using(banco).all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)

        if self.request.POST:
            context['formset'] = ItensPedidoFormSet(
                self.request.POST,
                form_kwargs={'database': banco, 'empresa_id': empresa_id}
            )
        else:
            # Pré-popular itens com dados existentes
            try:
                from .models import Itenspedidovenda
                from Entidades.models import Entidades
                from Produtos.models import Produtos
                pedido = self.object
                itens_qs = Itenspedidovenda.objects.using(banco).filter(
                    iped_empr=pedido.pedi_empr,
                    iped_fili=pedido.pedi_fili,
                    iped_pedi=str(pedido.pedi_nume)
                ).order_by('iped_item')
                initial = []
                codigos = []
                for i in itens_qs:
                    initial.append({
                        'iped_prod': i.iped_prod,
                        'iped_quan': i.iped_quan,
                        'iped_unit': i.iped_unit,
                        'iped_desc': i.iped_desc or 0,
                    })
                    codigos.append(i.iped_prod)

                # Nomes de cliente e vendedor
                cl = Entidades.objects.using(banco).filter(enti_clie=pedido.pedi_forn).values('enti_nome').first()
                ve = Entidades.objects.using(banco).filter(enti_clie=pedido.pedi_vend).values('enti_nome').first()
                context['cliente_display'] = f"{pedido.pedi_forn} - {cl.get('enti_nome')}" if cl else str(pedido.pedi_forn)
                context['vendedor_display'] = f"{pedido.pedi_vend} - {ve.get('enti_nome')}" if ve else str(pedido.pedi_vend)

                # Mapear nomes de produtos para preencher inputs de autocomplete
                produtos = Produtos.objects.using(banco).filter(prod_codi__in=codigos)
                prod_map = {p.prod_codi: f"{p.prod_codi} - {p.prod_nome}" for p in produtos}
                for idx, init in enumerate(initial):
                    init['display_prod_text'] = prod_map.get(init.get('iped_prod'), init.get('iped_prod'))
            except Exception:
                initial = []

            context['formset'] = ItensPedidoFormSet(
                initial=initial,
                form_kwargs={'database': banco, 'empresa_id': empresa_id}
            )

        context['slug'] = self.kwargs.get('slug')
        context['is_edit'] = True
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset_itens = context['formset']

        banco = get_licenca_db_config(self.request) or 'default'

        logger.debug("[PedidoUpdateView] Form valid=%s Formset valid=%s", form.is_valid(), formset_itens.is_valid())
        if form.is_valid() and formset_itens.is_valid():
            try:
                pedido = self.object
                pedido_updates = form.cleaned_data.copy()

                # Converter objetos Entidades em IDs
                if hasattr(pedido_updates.get('pedi_forn'), 'enti_clie'):
                    pedido_updates['pedi_forn'] = pedido_updates['pedi_forn'].enti_clie
                if hasattr(pedido_updates.get('pedi_vend'), 'enti_clie'):
                    pedido_updates['pedi_vend'] = pedido_updates['pedi_vend'].enti_clie

                logger.debug(
                    "[PedidoUpdateView] Atualização pedido pedi_nume=%s pedi_desc=%s pedi_topr=%s",
                    getattr(pedido, 'pedi_nume', None),
                    pedido_updates.get('pedi_desc'),
                    pedido_updates.get('pedi_topr'),
                )

                # Extrair itens
                itens_data = []
                for item_form in formset_itens.forms:
                    if not item_form.cleaned_data:
                        continue
                    if item_form.cleaned_data.get('DELETE'):
                        continue
                    item_data = item_form.cleaned_data.copy()
                    # Converter Produto para código
                    if hasattr(item_data.get('iped_prod'), 'prod_codi'):
                        item_data['iped_prod'] = item_data['iped_prod'].prod_codi
                    logger.debug(
                        "[PedidoUpdateView] Item: prod=%s quan=%s unit=%s desc=%s",
                        item_data.get('iped_prod'),
                        item_data.get('iped_quan', 1),
                        item_data.get('iped_unit', 0),
                        item_data.get('iped_desc', 0),
                    )
                    itens_data.append({
                        'iped_prod': item_data.get('iped_prod'),
                        'iped_quan': item_data.get('iped_quan', 1),
                        'iped_unit': item_data.get('iped_unit', 0),
                        'iped_desc': item_data.get('iped_desc', 0),
                    })

                if not itens_data:
                    messages.error(self.request, "O pedido precisa ter pelo menos um item.")
                    return self.form_invalid(form)

                logger.debug("[PedidoUpdateView] Chamando service.update_pedido_venda com %d itens", len(itens_data))
                PedidoVendaService.update_pedido_venda(
                    banco,
                    pedido,
                    pedido_updates,
                    itens_data,
                )
                logger.debug(
                    "[PedidoUpdateView] Pedido atualizado pedi_nume=%s pedi_topr=%s pedi_desc=%s pedi_tota=%s",
                    getattr(pedido, 'pedi_nume', None), getattr(pedido, 'pedi_topr', None), getattr(pedido, 'pedi_desc', None), getattr(pedido, 'pedi_tota', None)
                )
                messages.success(self.request, f"Pedido {pedido.pedi_nume} atualizado com sucesso.")
                return redirect(self.get_success_url())
            except Exception as e:
                messages.error(self.request, f"Erro ao atualizar pedido: {str(e)}")
                import traceback
                logger.exception("[PedidoUpdateView] Falha ao atualizar pedido: %s", e)
                traceback.print_exc()
                return self.form_invalid(form)
        else:
            if not form.is_valid():
                logger.error("[PedidoUpdateView] Erros no form: %s", form.errors)
                messages.error(self.request, f"Erros no formulário: {form.errors}")
            if not formset_itens.is_valid():
                logger.error("[PedidoUpdateView] Erros no formset: %s", formset_itens.errors)
                messages.error(self.request, f"Erros nos itens: {formset_itens.errors}")
            return self.form_invalid(form)