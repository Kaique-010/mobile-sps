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
from .models import EntradaEstoque
from .forms import EntradaEstoqueForm
from .formssets import ItensEntradaFormSet
from .services.entrada_service import EntradaEstoqueService, proximo_entrada_numero 
from django.db.models import Subquery, OuterRef, BigIntegerField
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


class EntradaCreateView(CreateView):
    model = EntradaEstoque
    form_class = EntradaEstoqueForm
    template_name = 'Entradas/entradocriar.html'


    def get_success_url(self):
        slug = self.kwargs.get('slug')
        return f"/web/{slug}/entradas/" if slug else "/web/home/"

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
        
        logger.debug("[EntradaCreateView] Form valid=%s Formset valid=%s", form.is_valid(), formset_itens.is_valid())
        if form.is_valid() and formset_itens.is_valid():
            try:
                # Prepara dados da entrada
                entrada_data = form.cleaned_data.copy()
                entrada_data['entr_empr'] = empresa_id
                entrada_data['entr_fili'] = filial_id
            except Exception as e:
                logger.error(f"Erro ao processar dados da entrada: {e}")
                return self.form_invalid(form)


               


class EntradaListView(ListView):
    model = EntradaEstoque
    template_name = 'Entradas/entradas_listar.html'
    context_object_name = 'entradas'
    paginate_by = 50
    
    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        from Entidades.models import Entidades
        
        qs = EntradaEstoque.objects.using(banco).all()
        
        # Filtros
        entidade = (self.request.GET.get('entidade') or '').strip()


        if entidade:
            if entidade.isdigit():
                qs = qs.filter(entr_enti__icontains=entidade)
            else:
                entidades_ids = list(
                    Entidades.objects.using(banco)
                    .filter(enti_nome__icontains=entidade)
                    .values_list('enti_clie', flat=True)[:200]
                )
                if entidades_ids:
                    qs = qs.filter(entr_enti__in=entidades_ids) 
                else:
                    qs = qs.none()   # Nenhum resultado se não houver IDs

        # Anotar nomes
        entidade = (
            Entidades.objects.using(banco)
            .filter(enti_clie=Cast(OuterRef('entr_enti'), BigIntegerField()))
            .values('enti_nome')[:1]
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')

        # Preservar filtros na paginação
        params = []
        for key in ['cliente', 'vendedor', 'status']:
            val = (self.request.GET.get(key) or '').strip()
            if val:
                params.append(f"{quote_plus(key)}={quote_plus(val)}")
        context['extra_query'] = "&".join(params)
        return context


class EntradaDetailView(DetailView):
    model = EntradaEstoque
    template_name = 'Entradas/entrada_detalhe.html'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        return EntradaEstoque.objects.using(banco).all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')
        
        try:
            from Entidades.models import Entidades
            from Produtos.models import Produtos
            banco = get_licenca_db_config(self.request) or 'default'
            entrada = context.get('object')
            
            if entrada:
                entidade = Entidades.objects.using(banco).filter(
                    enti_clie=entrada.entr_enti
                ).values('enti_nome').first()
        except Exception as e:
                logger.error(f"Erro ao carregar entidade: {e}")
                entidade = None
                                




class EntradaUpdateView(UpdateView):
    model = EntradaEstoque
    form_class = EntradaEstoqueForm
    template_name = 'Entradas/entrada_criar.html'

    def get_success_url(self):
        slug = self.kwargs.get('slug')
        return f"/web/{slug}/entradas/" if slug else "/web/home/"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['database'] = get_licenca_db_config(self.request) or 'default'
        kwargs['empresa_id'] = self.request.session.get('empresa_id', 1)
        return kwargs

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        return EntradaEstoque.objects.using(banco).all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)


    def form_valid(self, form):
        context = self.get_context_data()
        formset_itens = context['formset']

        banco = get_licenca_db_config(self.request) or 'default'

        logger.debug("[EntradaUpdateView] Form valid=%s Formset valid=%s", form.is_valid(), formset_itens.is_valid())
        if form.is_valid() and formset_itens.is_valid():
            try:
                entrada = self.object
                entrada_updates = form.cleaned_data.copy()

                # Converter objetos Entidades em IDs
                if hasattr(entrada_updates.get('entr_enti'), 'enti_clie'):
                    entrada_updates['entr_enti'] = entrada_updates['entr_enti'].enti_clie
                if hasattr(entrada_updates.get('entr_forn'), 'enti_clie'):
                    entrada_updates['entr_forn'] = entrada_updates['entr_forn'].enti_clie

                logger.debug(
                    "[EntradaUpdateView] Atualização entrada entr_nume=%s entr_enti=%s entr_forn=%s",
                    entrada.entr_nume, entrada_updates.get('entr_enti'), entrada_updates.get('entr_forn')
                )
            except Exception as e:
                logger.error(f"Erro ao atualizar entrada: {e}")
                return self.form_invalid(form)
