from django.views.generic import CreateView, ListView, DetailView
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from core.utils import get_licenca_db_config, calcular_subtotal_item_bruto, calcular_total_item_com_desconto
from .models import Orcamentos, ItensOrcamento
from .forms import OrcamentoVendaForm
from .formssets import ItensOrcamentoFormSet


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

        return JsonResponse({'unit_price': unit_price, 'found': True})
    except Exception as e:
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
                form_kwargs={'database': banco, 'empresa_id': empresa_id}
            )
        else:
            context['formset'] = ItensOrcamentoFormSet(
                form_kwargs={'database': banco, 'empresa_id': empresa_id}
            )
        context['slug'] = self.kwargs.get('slug')
        return context

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)

        formset = ItensOrcamentoFormSet(self.request.POST, form_kwargs={'database': banco, 'empresa_id': empresa_id})
        if not formset.is_valid():
            messages.error(self.request, 'Verifique os itens do orçamento.')
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
        total_orcamento = Decimal('0.00')
        for idx, item_form in enumerate(formset, start=1):
            # Usar Decimal para cálculos monetários
            iped_quan = item_form.cleaned_data.get('iped_quan')
            iped_unit = item_form.cleaned_data.get('iped_unit')
            # Garantir tipos Decimal mesmo se vierem como float/str
            iped_quan = Decimal(str(iped_quan or 0))
            iped_unit = Decimal(str(iped_unit or 0))

            subtotal_bruto = calcular_subtotal_item_bruto(iped_quan, iped_unit)
            total_item = calcular_total_item_com_desconto(iped_quan, iped_unit, 0)
            total_orcamento += Decimal(str(total_item))
            itens_data.append({
                'iped_item': idx,
                'iped_prod': str(item_form.cleaned_data.get('iped_prod') or ''),
                'iped_quan': iped_quan,
                'iped_unit': iped_unit,
                'iped_suto': subtotal_bruto,
                'iped_tota': total_item,
            })

        orcamento.pedi_tota = total_orcamento
        orcamento.save(using=banco)

        # Persistir itens
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
            )

        messages.success(self.request, f'Orçamento #{orcamento.pedi_nume} criado com sucesso.')
        return redirect(self.get_success_url())


class OrcamentosListView(ListView):
    model = Orcamentos
    template_name = 'Orcamentos/orcamentos_listar.html'
    context_object_name = 'orcamentos'
    paginate_by = 50

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)
        qs = Orcamentos.objects.using(banco).filter(pedi_empr=empresa_id, pedi_fili=filial_id)

        cliente = (self.request.GET.get('cliente') or '').strip()
        vendedor = (self.request.GET.get('vendedor') or '').strip()
        if cliente:
            qs = qs.filter(pedi_forn__icontains=cliente)
        if vendedor:
            qs = qs.filter(pedi_vend__icontains=vendedor)
        return qs.order_by('-pedi_data', '-pedi_nume')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')
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