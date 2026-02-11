from django.views.generic import CreateView, ListView, DetailView, UpdateView
import logging
from django.shortcuts import render, redirect
from urllib.parse import quote_plus
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.db.models import Subquery, OuterRef, BigIntegerField, Sum, Count
from django.db.models.functions import Cast
from core.utils import get_licenca_db_config, calcular_subtotal_item_bruto, calcular_total_item_com_desconto

logger = logging.getLogger(__name__)
from ..models import Orcamentos, ItensOrcamento
from .forms import OrcamentoVendaForm
from .formssets import ItensOrcamentoFormSet


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
    # Orçamentos não têm tipo financeiro, usar preço padrão (prazo)
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

        price = tp.tabe_praz or tp.tabe_prco or tp.tabe_avis
        try:
            unit_price = float(price or 0)
        except Exception:
            unit_price = 0.0

        logger.debug(
            "[Orcamentos.preco_produto] prod_codi=%s price_source=praz/prco/avis unit_price=%.2f",
            prod_codi, unit_price
        )
        return JsonResponse({'unit_price': unit_price, 'found': True})
    except Exception as e:
        logger.exception("[Orcamentos.preco_produto] Erro ao calcular preço: %s", e)
        return JsonResponse({'error': str(e)}, status=500)


class OrcamentoCreateView(CreateView):
    model = Orcamentos
    form_class = OrcamentoVendaForm
    template_name = 'Orcamentos/orcamentocriar.html'

    def get_success_url(self):
        slug = self.kwargs.get('slug')
        return f"/web/{slug}/orcamentos/" if slug else "/web/home/"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['database'] = get_licenca_db_config(self.request) or 'default'
        kwargs['empresa_id'] = self.request.session.get('empresa_id', 1)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)
        if self.request.POST:
            context['formset'] = ItensOrcamentoFormSet(
                self.request.POST,
                form_kwargs={'database': banco, 'empresa_id': empresa_id},
                prefix='form'
            )
        else:
            context['formset'] = ItensOrcamentoFormSet(
                form_kwargs={'database': banco, 'empresa_id': empresa_id},
                prefix='form'
            )
        context['slug'] = self.kwargs.get('slug')
        return context

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)

        formset = ItensOrcamentoFormSet(
            self.request.POST,
            form_kwargs={'database': banco, 'empresa_id': empresa_id},
            prefix='form'
        )
        logger.debug("[OrcamentoCreateView] Form valid=%s Formset valid=%s", form.is_valid(), formset.is_valid())
        if not formset.is_valid():
            messages.error(self.request, 'Verifique os itens do orçamento.')
            logger.error("[OrcamentoCreateView] Erros no formset: %s", formset.errors)
            return self.form_invalid(form)

        # Obter próximo número
        ultimo = (
            Orcamentos.objects.using(banco)
            .filter(pedi_empr=empresa_id, pedi_fili=filial_id)
            .order_by('-pedi_nume')
            .first()
        )
        proximo_numero = (ultimo.pedi_nume + 1) if ultimo else 1
        while Orcamentos.objects.using(banco).filter(pedi_nume=proximo_numero).exists():
            proximo_numero += 1

        orcamento = form.save(commit=False)
        orcamento.pedi_empr = empresa_id
        orcamento.pedi_fili = filial_id
        orcamento.pedi_nume = proximo_numero

        # Total do orçamento a partir dos itens
        from decimal import Decimal
        itens_data = []
        subtotal_orcamento = Decimal('0.00')
        const_desconto = Decimal(str(form.cleaned_data.get('pedi_desc') or 0))
        logger.debug(
            "[OrcamentoCreateView] Início cálculo: pedi_desc=%s proximo=%s",
            form.cleaned_data.get('pedi_desc'), proximo_numero
        )
        for idx, item_form in enumerate(formset, start=1):
            # Ignorar itens marcados para deleção
            if item_form.cleaned_data.get('DELETE'):
                continue
            # Usar Decimal para cálculos monetários
            iped_quan = item_form.cleaned_data.get('iped_quan')
            iped_unit = item_form.cleaned_data.get('iped_unit')
            # Garantir tipos Decimal mesmo se vierem como float/str
            iped_quan = Decimal(str(iped_quan or 0))
            iped_unit = Decimal(str(iped_unit or 0))

            subtotal_bruto = calcular_subtotal_item_bruto(iped_quan, iped_unit)
            total_item = calcular_total_item_com_desconto(iped_quan, iped_unit, 0)
            subtotal_orcamento += Decimal(str(subtotal_bruto))
            logger.debug(
                "[OrcamentoCreateView] Item %d: prod=%s quan=%s unit=%s subtotal=%s total_item=%s",
                idx,
                str(item_form.cleaned_data.get('iped_prod') or ''),
                iped_quan,
                iped_unit,
                subtotal_bruto,
                total_item,
            )
            itens_data.append({
                'iped_item': idx,
                'iped_prod': str(item_form.cleaned_data.get('iped_prod') or ''),
                'iped_quan': iped_quan,
                'iped_unit': iped_unit,
                'iped_suto': subtotal_bruto,
                'iped_tota': total_item,
            })
        # Aplicar desconto total (se informado) e definir subtotal
        orcamento.pedi_topr = subtotal_orcamento
        orcamento.pedi_desc = const_desconto
        orcamento.pedi_tota = max(subtotal_orcamento - const_desconto, Decimal('0.00'))
        orcamento.save(using=banco)

        logger.debug(
            "[OrcamentoCreateView] Totais: subtotal=%s desconto=%s total=%s",
            orcamento.pedi_topr, orcamento.pedi_desc, orcamento.pedi_tota
        )

        # Persistir itens
        if not itens_data:
            messages.error(self.request, 'Inclua ao menos um item válido no orçamento.')
            return self.form_invalid(form)
        try:
            for item in itens_data:
                ItensOrcamento.objects.using(banco).create(
                    iped_empr=empresa_id,
                    iped_fili=filial_id,
                    iped_pedi=str(orcamento.pedi_nume),
                    iped_item=item['iped_item'],
                    iped_prod=item['iped_prod'],
                    iped_quan=item['iped_quan'],
                    iped_unit=item['iped_unit'],
                    iped_suto=item['iped_suto'],
                    iped_tota=item['iped_tota'],
                    iped_data=orcamento.pedi_data,
                )
        except Exception as e:
            logger.exception("[OrcamentoCreateView] Erro ao salvar itens: %s", e)
            messages.error(self.request, f'Erro ao salvar itens: {e}')
            return self.form_invalid(form)

        messages.success(self.request, f'Orçamento #{orcamento.pedi_nume} criado com sucesso.')
        return redirect(self.get_success_url())


class OrcamentosListView(ListView):
    model = Orcamentos
    template_name = 'Orcamentos/orcamentos_listar.html'
    context_object_name = 'orcamentos'
    paginate_by = 50

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        from Entidades.models import Entidadess
        
        qs = Orcamentos.objects.using(banco).filter(
            pedi_empr=self.request.session.get('empresa_id', 1),
            pedi_fili=self.request.session.get('filial_id', 1),
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
            qs = qs.filter(pedi_stat=status)

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
        from Entidades.models import Entidadess
        qs_total = Orcamentos.objects.using(banco).filter(
            pedi_empr=self.request.session.get('empresa_id', 1),
            pedi_fili=self.request.session.get('filial_id', 1),
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
            qs_total = qs_total.filter(pedi_stat=status)

        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)
        qs_total = qs_total.filter(pedi_empr=empresa_id, pedi_fili=filial_id)
        context['total_registros'] = qs_total.count()
        context['total_valor'] = qs_total.aggregate(Sum('pedi_tota'))['pedi_tota__sum'] or 0

        # Cards de resumo
        distintos_clientes = qs_total.values('pedi_forn').distinct().count()
        context['cards_resumo'] = [
            {'label': 'Total de Orçamentos', 'qtd': context['total_registros'], 'valor': context['total_valor'], 'color': '#4a6cf7'},
            {'label': 'Clientes Distintos', 'qtd': distintos_clientes, 'valor': None, 'color': '#6ec1e4'},
        ]

        # Cards por status
        STATUS_ORC = [
            {'value': 'A', 'label': 'Aberto'},
            {'value': 'F', 'label': 'Faturado'},
            {'value': 'C', 'label': 'Cancelado'},
        ]
        MAP_CORES_ORC = {'A': '#FFC107', 'F': '#28A745', 'C': '#6C757D'}
        agg = list(qs_total.values('pedi_stat').annotate(qtd=Count('pedi_nume'), valor=Sum('pedi_tota')))
        by_status = {str(a['pedi_stat']): a for a in agg}
        cards_status = []
        for s in STATUS_ORC:
            k = str(s['value'])
            a = by_status.get(k, {'qtd': 0, 'valor': 0})
            cards_status.append({
                'status': k,
                'label': s['label'],
                'color': MAP_CORES_ORC.get(k, '#6C757D'),
                'qtd': int(a.get('qtd') or 0),
                'valor': float(a.get('valor') or 0),
            })
        context['cards_por_status'] = cards_status

        params = []
        for key in ['cliente', 'vendedor', 'status']:
            val = (self.request.GET.get(key) or '').strip()
            if val:
                params.append(f"{quote_plus(key)}={quote_plus(val)}")
        context['extra_query'] = ("&" + "&".join(params)) if params else ""
        return context


class OrcamentoDetailView(DetailView):
    model = Orcamentos
    template_name = 'Orcamentos/orcamento_detalhe.html'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)
        return Orcamentos.objects.using(banco).filter(pedi_empr=empresa_id, pedi_fili=filial_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')
        # Itens
        banco = get_licenca_db_config(self.request) or 'default'
        obj = self.object
        itens_qs = ItensOrcamento.objects.using(banco).filter(
            iped_empr=obj.pedi_empr, iped_fili=obj.pedi_fili, iped_pedi=str(obj.pedi_nume)
        ).order_by('iped_item')

        # Enriquecer itens com nome e foto do produto
        try:
            from Produtos.models import Produtos
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
        except Exception:
            context['itens_detalhados'] = [{'prod_codigo': i.iped_prod, 'prod_nome': i.iped_prod, 'has_foto': False,
                                             'iped_quan': i.iped_quan, 'iped_unit': i.iped_unit, 'iped_tota': i.iped_tota,
                                             'iped_item': getattr(i, 'iped_item', None)} for i in itens_qs]
        return context


class OrcamentoPrintView(DetailView):
    model = Orcamentos
    template_name = 'Orcamentos/orcamento_impressao.html'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)
        return Orcamentos.objects.using(banco).filter(pedi_empr=empresa_id, pedi_fili=filial_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')
        banco = get_licenca_db_config(self.request) or 'default'
        obj = self.object
        itens_qs = ItensOrcamento.objects.using(banco).filter(
            iped_empr=obj.pedi_empr, iped_fili=obj.pedi_fili, iped_pedi=str(obj.pedi_nume)
        ).order_by('iped_item')

        # Enriquecer itens com nome e foto para impressão
        try:
            from Produtos.models import Produtos
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
        except Exception:
            context['itens_detalhados'] = [{'prod_codigo': i.iped_prod, 'prod_nome': i.iped_prod, 'has_foto': False,
                                             'iped_quan': i.iped_quan, 'iped_unit': i.iped_unit, 'iped_tota': i.iped_tota,
                                             'iped_item': getattr(i, 'iped_item', None)} for i in itens_qs]
        return context


class OrcamentoUpdateView(UpdateView):
    model = Orcamentos
    form_class = OrcamentoVendaForm
    template_name = 'Orcamentos/orcamentocriar.html'

    def get_success_url(self):
        slug = self.kwargs.get('slug')
        return f"/web/{slug}/orcamentos/" if slug else "/web/home/"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['database'] = get_licenca_db_config(self.request) or 'default'
        kwargs['empresa_id'] = self.request.session.get('empresa_id', 1)
        return kwargs

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        return Orcamentos.objects.using(banco).all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)

        if self.request.POST:
            context['formset'] = ItensOrcamentoFormSet(
                self.request.POST,
                form_kwargs={'database': banco, 'empresa_id': empresa_id}
            )
        else:
            try:
                from Entidades.models import Entidades
                from Produtos.models import Produtos
                obj = self.object
                itens_qs = ItensOrcamento.objects.using(banco).filter(
                    iped_empr=obj.pedi_empr, iped_fili=obj.pedi_fili, iped_pedi=str(obj.pedi_nume)
                ).order_by('iped_item')
                initial = []
                codigos = []
                for i in itens_qs:
                    initial.append({
                        'iped_prod': i.iped_prod,
                        'iped_quan': i.iped_quan,
                        'iped_unit': i.iped_unit,
                    })
                    codigos.append(i.iped_prod)

                # Nomes de cliente e vendedor
                cl = Entidades.objects.using(banco).filter(enti_clie=obj.pedi_forn).values('enti_nome').first()
                ve = Entidades.objects.using(banco).filter(enti_clie=obj.pedi_vend).values('enti_nome').first()
                context['cliente_display'] = f"{obj.pedi_forn} - {cl.get('enti_nome')}" if cl else str(obj.pedi_forn)
                context['vendedor_display'] = f"{obj.pedi_vend} - {ve.get('enti_nome')}" if ve else str(obj.pedi_vend)

                # Mapear nomes de produtos
                produtos = Produtos.objects.using(banco).filter(prod_codi__in=codigos)
                prod_map = {p.prod_codi: f"{p.prod_codi} - {p.prod_nome}" for p in produtos}
                for init in initial:
                    init['display_prod_text'] = prod_map.get(init.get('iped_prod'), init.get('iped_prod'))
            except Exception:
                initial = []

            context['formset'] = ItensOrcamentoFormSet(
                initial=initial,
                form_kwargs={'database': banco, 'empresa_id': empresa_id}
            )

        context['slug'] = self.kwargs.get('slug')
        context['is_edit'] = True
        return context

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)

        formset = ItensOrcamentoFormSet(self.request.POST, form_kwargs={'database': banco, 'empresa_id': empresa_id})
        logger.debug("[OrcamentoUpdateView] Form valid=%s Formset valid=%s", form.is_valid(), formset.is_valid())
        if not formset.is_valid():
            messages.error(self.request, 'Verifique os itens do orçamento.')
            logger.error("[OrcamentoUpdateView] Erros no formset: %s", formset.errors)
            return self.form_invalid(form)

        from decimal import Decimal
        obj = self.object
        itens_data = []
        subtotal_orcamento = Decimal('0.00')
        const_desconto = Decimal(str(form.cleaned_data.get('pedi_desc') or 0))
        logger.debug(
            "[OrcamentoUpdateView] Início cálculo update: pedi_nume=%s pedi_desc=%s",
            getattr(obj, 'pedi_nume', None), form.cleaned_data.get('pedi_desc')
        )
        for idx, item_form in enumerate(formset, start=1):
            if item_form.cleaned_data.get('DELETE'):
                continue
            iped_quan = item_form.cleaned_data.get('iped_quan')
            iped_unit = item_form.cleaned_data.get('iped_unit')
            iped_quan = Decimal(str(iped_quan or 0))
            iped_unit = Decimal(str(iped_unit or 0))

            subtotal_bruto = calcular_subtotal_item_bruto(iped_quan, iped_unit)
            total_item = calcular_total_item_com_desconto(iped_quan, iped_unit, 0)
            subtotal_orcamento += Decimal(str(subtotal_bruto))
            logger.debug(
                "[OrcamentoUpdateView] Item %d: prod=%s quan=%s unit=%s subtotal=%s total_item=%s",
                idx,
                str(item_form.cleaned_data.get('iped_prod') or ''),
                iped_quan,
                iped_unit,
                subtotal_bruto,
                total_item,
            )
            itens_data.append({
                'iped_item': idx,
                'iped_prod': str(item_form.cleaned_data.get('iped_prod') or ''),
                'iped_quan': iped_quan,
                'iped_unit': iped_unit,
                'iped_suto': subtotal_bruto,
                'iped_tota': total_item,
            })

        # Atualizar orcamento com subtotal e desconto
        obj.pedi_topr = subtotal_orcamento
        obj.pedi_desc = const_desconto
        obj.pedi_tota = max(subtotal_orcamento - const_desconto, Decimal('0.00'))
        obj.save(using=banco)

        logger.debug(
            "[OrcamentoUpdateView] Totais update: subtotal=%s desconto=%s total=%s",
            obj.pedi_topr, obj.pedi_desc, obj.pedi_tota
        )

        # Remover itens antigos e recriar
        ItensOrcamento.objects.using(banco).filter(
            iped_empr=obj.pedi_empr, iped_fili=obj.pedi_fili, iped_pedi=str(obj.pedi_nume)
        ).delete()

        for item in itens_data:
            ItensOrcamento.objects.using(banco).create(
                iped_empr=empresa_id,
                iped_fili=filial_id,
                iped_pedi=str(obj.pedi_nume),
                iped_item=item['iped_item'],
                iped_prod=item['iped_prod'],
                iped_quan=item['iped_quan'],
                iped_unit=item['iped_unit'],
                iped_suto=item['iped_suto'],
                iped_tota=item['iped_tota'],
            )

        messages.success(self.request, f'Orçamento #{obj.pedi_nume} atualizado com sucesso.')
        return redirect(self.get_success_url())