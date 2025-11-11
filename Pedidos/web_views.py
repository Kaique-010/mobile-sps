from django.views.generic import CreateView, ListView, DetailView
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from core.utils import get_licenca_db_config
from .models import PedidoVenda
from .forms import PedidoVendaForm, ItensPedidoVendaForm
from .formssets import ItensPedidoFormSet
from .services.pedido_service import PedidoVendaService
from django.db.models import Subquery, OuterRef, BigIntegerField
from django.db.models.functions import Cast

class PedidoCreateView(CreateView):
    model = PedidoVenda
    form_class = PedidoVendaForm
    template_name = 'Pedidos/pedidocriar.html'
    # success_url resolvida dinamicamente com slug

    def get_success_url(self):
        slug = self.kwargs.get('slug')
        return f"/web/{slug}/pedidos/" if slug else "/web/home/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = ItensPedidoFormSet(self.request.POST)
        else:
            context['formset'] = ItensPedidoFormSet()
        # Carregar produtos para o select dos itens
        try:
            from Produtos.models import Produtos
            banco = get_licenca_db_config(self.request) or 'default'
            qs = Produtos.objects.using(banco).all()
            empresa_id = self.request.session.get('empresa_id')
            if empresa_id:
                qs = qs.filter(prod_empr=str(empresa_id))
            context['produtos'] = qs.order_by('prod_nome')[:100]
        except Exception:
            context['produtos'] = []
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset_itens = context['formset']

        # Injetar empresa/filial da sessão
        empresa_id = self.request.session.get('empresa_id') or 1
        filial_id = self.request.session.get('filial_id') or 1
        form.cleaned_data['pedi_empr'] = empresa_id
        form.cleaned_data['pedi_fili'] = filial_id

        if form.is_valid() and formset_itens.is_valid():
            try:
                # Extrai dados dos itens do formset para lista de dicts
                itens_data = []
                for f in getattr(formset_itens, 'forms', []):
                    cd = getattr(f, 'cleaned_data', None)
                    if not cd:
                        continue
                    if cd.get('DELETE'):
                        continue
                    itens_data.append({
                        'iped_prod': cd.get('iped_prod'),
                        'iped_quan': cd.get('iped_quan'),
                        'iped_unit': cd.get('iped_unit'),
                        'iped_desc': cd.get('iped_desc', 0) or 0,
                    })

                pedido = PedidoVendaService.create_pedido_venda(
                    form.cleaned_data,
                    itens_data
                )
                messages.success(self.request, f"Pedido {pedido.pedi_nume} criado com sucesso.")
                return redirect(self.get_success_url())

            except Exception as e:
                messages.error(self.request, f"Erro ao salvar pedido: {e}")
                return self.form_invalid(form)
        else:
            messages.error(self.request, "Verifique os campos antes de enviar.")
        return self.form_invalid(form)


class PedidosListView(ListView):
    model = PedidoVenda
    template_name = 'Pedidos/pedidos_listar.html'
    context_object_name = 'pedidos'
    
    def vendedor_nome(self, pedi_vend):
        try:
            from Entidades.models import Entidades
            banco = get_licenca_db_config(self.request) or 'default'
            vendedor = Entidades.objects.using(banco).get(enti_clie=pedi_vend)
            return vendedor.enti_nome
        except Entidades.DoesNotExist:
            return "Vendedor Desconhecido"
    def cliente_nome(self, pedi_forn):
        try:
            from Entidades.models import Entidades
            banco = get_licenca_db_config(self.request) or 'default'
            cliente = Entidades.objects.using(banco).get(enti_clie=pedi_forn)
            return cliente.enti_nome
        except Entidades.DoesNotExist:
            return "Cliente Desconhecido"

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        from Entidades.models import Entidades
        qs = PedidoVenda.objects.using(banco).all()
        # Filtros simples via GET (alinhados com o template)
        cliente_param = (self.request.GET.get('cliente') or '').strip()
        vendedor_param = (self.request.GET.get('vendedor') or '').strip()
        status = self.request.GET.get('status')

        if cliente_param:
            # Se for número/código, filtra direto; senão, busca por nome em Entidades
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

        # Anotar nomes do cliente e vendedor usando subqueries
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
        # Enriquecer com nomes de cliente e vendedor
        try:
            from Entidades.models import Entidades
            banco = get_licenca_db_config(self.request) or 'default'
            pedido = context.get('object')
            if pedido:
                cliente = Entidades.objects.using(banco).filter(enti_clie=pedido.pedi_forn).values('enti_nome').first()
                vendedor = Entidades.objects.using(banco).filter(enti_clie=pedido.pedi_vend).values('enti_nome').first()
                context['cliente_nome'] = cliente.get('enti_nome') if cliente else None
                context['vendedor_nome'] = vendedor.get('enti_nome') if vendedor else None
        except Exception:
            context['cliente_nome'] = None
            context['vendedor_nome'] = None
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
        # Reutiliza a lógica de nomes para impressão
        try:
            from Entidades.models import Entidades
            banco = get_licenca_db_config(self.request) or 'default'
            pedido = context.get('object')
            if pedido:
                cliente = Entidades.objects.using(banco).filter(enti_clie=pedido.pedi_forn).values('enti_nome').first()
                vendedor = Entidades.objects.using(banco).filter(enti_clie=pedido.pedi_vend).values('enti_nome').first()
                context['cliente_nome'] = cliente.get('enti_nome') if cliente else None
                context['vendedor_nome'] = vendedor.get('enti_nome') if vendedor else None
        except Exception:
            context['cliente_nome'] = None
            context['vendedor_nome'] = None
        return context


# Views de edição/exclusão serão adicionadas futuramente
