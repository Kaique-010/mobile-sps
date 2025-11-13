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

from .models import Os 
from .forms import OsForm
from .formssets import PecasOsFormSet, ServicoOsFormSet  
from .services.os_service import OsService
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

class OsCreateView(CreateView):
    model = Os
    form_class = OsForm
    template_name = 'Os/oscriar.html'


    def get_success_url(self):
        slug = self.kwargs.get('slug')
        return f"/web/{slug}/os/" if slug else "/web/home/"

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
            context['pecas_formset'] = PecasOsFormSet(
                self.request.POST,
                form_kwargs={'database': banco, 'empresa_id': empresa_id},
                prefix='pecas'
            )
            context['servicos_formset'] = ServicoOsFormSet(
                self.request.POST,
                form_kwargs={'database': banco, 'empresa_id': empresa_id},
                prefix='servicos'
            )
        else:
            context['pecas_formset'] = PecasOsFormSet(
                form_kwargs={'database': banco, 'empresa_id': empresa_id},
                prefix='pecas'
            )
            context['servicos_formset'] = ServicoOsFormSet(
                form_kwargs={'database': banco, 'empresa_id': empresa_id},
                prefix='servicos'
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
        pecas_formset = context['pecas_formset']
        servicos_formset = context['servicos_formset']

        # Injetar empresa/filial da sessão
        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)
        banco = get_licenca_db_config(self.request) or 'default'
        
        logger.debug("[OsCreateView] Form valid=%s Pecas valid=%s Servicos valid=%s", form.is_valid(), pecas_formset.is_valid(), servicos_formset.is_valid())
        if form.is_valid() and pecas_formset.is_valid() and servicos_formset.is_valid():
            try:
                # Prepara dados da OS
                os_data = form.cleaned_data.copy()
                os_data['os_empr'] = empresa_id
                os_data['os_fili'] = filial_id
                os_data['os_desc'] = os_data.get('os_desc', 0)
                os_data['os_tota'] = os_data.get('os_tota', 0)
                os_data.pop('os_topr', None)
                
                # Converte objetos Entidades para IDs
                if hasattr(os_data.get('os_clie'), 'enti_clie'):
                    os_data['os_clie'] = os_data['os_clie'].enti_clie
                if hasattr(os_data.get('os_resp'), 'enti_clie'):
                    os_data['os_resp'] = os_data['os_resp'].enti_clie
                
                logger.debug(
                    "[OsCreateView] Dados da OS iniciais: os_clie=%s os_resp=%s os_desc=%s os_tota=%s",
                    getattr(os_data.get('os_clie'), 'enti_clie', os_data.get('os_clie')),
                    getattr(os_data.get('os_resp'), 'enti_clie', os_data.get('os_resp')),
                    os_data.get('os_desc'),
                    os_data.get('os_tota'),
                )

                pecas_data = []
                for item_form in pecas_formset.forms:
                    if not item_form.cleaned_data or item_form.cleaned_data.get('DELETE'):
                        continue
                    item_data = item_form.cleaned_data.copy()
                    prod = item_data.get('peca_prod')
                    prod_code = getattr(prod, 'prod_codi', prod)
                    pecas_data.append({
                        'peca_prod': prod_code,
                        'peca_quan': item_data.get('peca_quan', 1),
                        'peca_unit': item_data.get('peca_unit', 0),
                        'peca_desc': item_data.get('peca_desc', 0),
                    })

                servicos_data = []
                for item_form in servicos_formset.forms:
                    if not item_form.cleaned_data or item_form.cleaned_data.get('DELETE'):
                        continue
                    item_data = item_form.cleaned_data.copy()
                    prod = item_data.get('serv_prod')
                    prod_code = getattr(prod, 'prod_codi', prod)
                    servicos_data.append({
                        'serv_prod': prod_code,
                        'serv_quan': item_data.get('serv_quan', 1),
                        'serv_unit': item_data.get('serv_unit', 0),
                        'serv_desc': item_data.get('serv_desc', 0),
                    })

                if not pecas_data and not servicos_data:
                    messages.error(self.request, "A OS precisa ter pelo menos uma peça ou serviço.")
                    return self.form_invalid(form)

                logger.debug("[OsCreateView] Chamando service.create_os com %d peças e %d serviços", len(pecas_data), len(servicos_data))
                os = OsService.create_os(
                    banco,
                    os_data,
                    pecas_data,
                    servicos_data,
                )
                logger.debug(
                    "[OsCreateView] OS criada os_os=%s os_desc=%s os_tota=%s",
                    getattr(os, 'os_os', None), getattr(os, 'os_desc', None), getattr(os, 'os_tota', None)
                )
                messages.success(self.request, f"OS {os.os_os} criada com sucesso.")
                return redirect(self.get_success_url())

            except Exception as e:
                messages.error(self.request, f"Erro ao salvar OS: {str(e)}")
                logger.exception("[OsCreateView] Falha ao salvar OS: %s", e)
                import traceback
                traceback.print_exc()
                return self.form_invalid(form)
        else:
            # Mostra erros de validação
            if not form.is_valid():
                messages.error(self.request, f"Erros no formulário: {form.errors}")
            if not pecas_formset.is_valid() or not servicos_formset.is_valid():
                messages.error(self.request, "Erros nos itens de peças ou serviços.")
            return self.form_invalid(form)


class OsListView(ListView):
    model = Os
    template_name = 'Os/os_listar.html'
    context_object_name = 'os'
    paginate_by = 50
    
    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        from Entidades.models import Entidades
        
        qs = Os.objects.using(banco).all()
        
        # Filtros
        cliente_param = (self.request.GET.get('cliente') or '').strip()
        vendedor_param = (self.request.GET.get('vendedor') or '').strip()
        status = self.request.GET.get('status')

        if cliente_param:
            if cliente_param.isdigit():
                qs = qs.filter(os_clie__icontains=cliente_param)
            else:
                entidades_ids = list(
                    Entidades.objects.using(banco)
                    .filter(enti_nome__icontains=cliente_param)
                    .values_list('enti_clie', flat=True)[:200]
                )
                if entidades_ids:
                    qs = qs.filter(os_clie__in=entidades_ids)
                else:
                    qs = qs.none()

        if vendedor_param:
            if vendedor_param.isdigit():
                qs = qs.filter(os_resp__icontains=vendedor_param)
            else:
                vendedores_ids = list(
                    Entidades.objects.using(banco)
                    .filter(enti_nome__icontains=vendedor_param)
                    .values_list('enti_clie', flat=True)[:200]
                )
                if vendedores_ids:
                    qs = qs.filter(os_resp__in=vendedores_ids)
                else:
                    qs = qs.none()
                    
        if status not in (None, '', 'todos'):
            qs = qs.filter(os_stat_os=status)

        # Anotar nomes
        cliente_nome_subq = (
            Entidades.objects.using(banco)
            .filter(enti_clie=Cast(OuterRef('os_clie'), BigIntegerField())) 
            .values('enti_nome')[:1]
        )
        vendedor_nome_subq = (
            Entidades.objects.using(banco)
            .filter(enti_clie=Cast(OuterRef('os_resp'), BigIntegerField()))
            .values('enti_nome')[:1]
        )
        qs = qs.annotate(
            cliente_nome=Subquery(cliente_nome_subq),
            vendedor_nome=Subquery(vendedor_nome_subq)
        ).order_by('-os_data_aber', '-os_os')

        return qs

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


class OsDetailView(DetailView):
    model = Os
    template_name = 'Os/os_detalhe.html'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        return Os.objects.using(banco).all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')
        
        try:
            from Entidades.models import Entidades
            from Produtos.models import Produtos
            banco = get_licenca_db_config(self.request) or 'default'
            os = context.get('object')
            
            if os:
                cliente = Entidades.objects.using(banco).filter(
                    enti_clie=os.os_clie
                ).values('enti_nome').first()
                vendedor = Entidades.objects.using(banco).filter(
                    enti_clie=os.os_resp
                ).values('enti_nome').first()
                
                context['cliente_nome'] = cliente.get('enti_nome') if cliente else 'N/A'
                context['vendedor_nome'] = vendedor.get('enti_nome') if vendedor else 'N/A'

                # Itens detalhados com nome e foto do produto
                itens_qs = (
                    os.itens if hasattr(os, 'itens') else []
                )
                # Preferir consulta explícita usando o banco correto
                try:
                    itens_qs = Produtos.objects.none()  # placeholder para tipo
                    from .models import ItensOs
                    itens_qs = ItensOs.objects.using(banco).filter(
                        iped_empr=os.os_empr,
                        iped_fili=os.os_fili,
                        iped_os=str(os.os_nume)
                    ).order_by('peca_os')
                except Exception:
                    pass

                codigos = [i.peca_os for i in itens_qs]
                produtos = Produtos.objects.using(banco).filter(prod_codi__in=codigos)
                prod_map = {p.prod_codi: {'nome': p.prod_nome, 'has_foto': bool(p.prod_foto)} for p in produtos}

                itens_detalhados = []
                for i in itens_qs:
                    meta = prod_map.get(i.peca_os, {})
                    itens_detalhados.append({
                        'prod_codigo': i.peca_os,
                        'prod_nome': meta.get('nome') or i.peca_os,
                        'has_foto': bool(meta.get('has_foto')), 
                        'peca_quan': i.peca_quan,
                        'peca_unit': i.peca_unit,   
                        'peca_tota': i.peca_tota,
                        'peca_item': getattr(i, 'peca_item', None),
                    })
                context['itens_detalhados'] = itens_detalhados
        except Exception as e:
            print(f"Erro ao carregar nomes: {e}")
            context['cliente_nome'] = 'N/A'
            context['vendedor_nome'] = 'N/A'
            
        return context


class OsPrintView(DetailView):
    model = Os
    template_name = 'Os/os_impressao.html'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        return Os.objects.using(banco).all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')
        
        try:
            from Entidades.models import Entidades
            from Produtos.models import Produtos
            banco = get_licenca_db_config(self.request) or 'default'
            os = context.get('object')
            
            if os:
                cliente = Entidades.objects.using(banco).filter(
                    enti_clie=os.os_forn
                ).values('enti_nome').first()
                vendedor = Entidades.objects.using(banco).filter(
                    enti_clie=os.os_vend
                ).values('enti_nome').first()
                
                context['cliente_nome'] = cliente.get('enti_nome') if cliente else 'N/A'
                context['vendedor_nome'] = vendedor.get('enti_nome') if vendedor else 'N/A'

                context['itens_detalhados'] = []
        except Exception as e:
            print(f"Erro ao carregar nomes: {e}")
            context['cliente_nome'] = 'N/A'
            context['vendedor_nome'] = 'N/A'
            
        return context


class OsUpdateView(UpdateView):
    model = Os
    form_class = OsForm
    template_name = 'Os/oscriar.html'

    def get_success_url(self):
        slug = self.kwargs.get('slug')
        return f"/web/{slug}/os/" if slug else "/web/home/"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['database'] = get_licenca_db_config(self.request) or 'default'
        kwargs['empresa_id'] = self.request.session.get('empresa_id', 1)
        return kwargs

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        return Os.objects.using(banco).all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)

        from Entidades.models import Entidades
        from Produtos.models import Produtos
        os_obj = self.object

        if self.request.POST:
            context['pecas_formset'] = PecasOsFormSet(
                self.request.POST,
                form_kwargs={'database': banco, 'empresa_id': empresa_id},
                prefix='pecas'
            )
            context['servicos_formset'] = ServicoOsFormSet(
                self.request.POST,
                form_kwargs={'database': banco, 'empresa_id': empresa_id},
                prefix='servicos'
            )
        else:
            from .models import PecasOs, ServicosOs
            pecas_qs = PecasOs.objects.using(banco).filter(
                peca_empr=os_obj.os_empr,
                peca_fili=os_obj.os_fili,
                peca_os=os_obj.os_os,
            ).order_by('peca_item')
            servicos_qs = ServicosOs.objects.using(banco).filter(
                serv_empr=os_obj.os_empr,
                serv_fili=os_obj.os_fili,
                serv_os=os_obj.os_os,
            ).order_by('serv_item')

            pecas_initial = []
            servicos_initial = []
            pecas_codigos = []
            serv_codigos = []
            for p in pecas_qs:
                pecas_initial.append({
                    'peca_prod': p.peca_prod,
                    'peca_quan': p.peca_quan,
                    'peca_unit': p.peca_unit,
                    'peca_desc': p.peca_desc or 0,
                    'peca_tota': p.peca_tota,
                })
                if p.peca_prod:
                    pecas_codigos.append(p.peca_prod)
            for s in servicos_qs:
                servicos_initial.append({
                    'serv_prod': s.serv_prod,
                    'serv_quan': s.serv_quan,
                    'serv_unit': s.serv_unit,
                    'serv_desc': s.serv_desc or 0,
                    'serv_tota': s.serv_tota,
                })
                if s.serv_prod:
                    serv_codigos.append(s.serv_prod)

            # Mapas de exibição para inputs de autocomplete
            prod_map = {}
            try:
                produtos = Produtos.objects.using(banco).filter(prod_codi__in=list(set(pecas_codigos + serv_codigos)))
                prod_map = {p.prod_codi: f"{p.prod_codi} - {p.prod_nome}" for p in produtos}
            except Exception:
                prod_map = {}
            for init in pecas_initial:
                init['display_prod_text'] = prod_map.get(init.get('peca_prod'), init.get('peca_prod'))
            for init in servicos_initial:
                init['display_prod_text'] = prod_map.get(init.get('serv_prod'), init.get('serv_prod'))

            context['pecas_formset'] = PecasOsFormSet(
                initial=pecas_initial,
                form_kwargs={'database': banco, 'empresa_id': empresa_id},
                prefix='pecas'
            )
            context['servicos_formset'] = ServicoOsFormSet(
                initial=servicos_initial,
                form_kwargs={'database': banco, 'empresa_id': empresa_id},
                prefix='servicos'
            )

            # Exibir nomes de cliente e responsável
            cl = Entidades.objects.using(banco).filter(enti_clie=os_obj.os_clie).values('enti_nome').first()
            ve = Entidades.objects.using(banco).filter(enti_clie=os_obj.os_resp).values('enti_nome').first()
            context['cliente_display'] = f"{os_obj.os_clie} - {cl.get('enti_nome')}" if cl else str(os_obj.os_clie)
            context['vendedor_display'] = f"{os_obj.os_resp} - {ve.get('enti_nome')}" if ve else str(os_obj.os_resp)

        context['slug'] = self.kwargs.get('slug')
        context['is_edit'] = True
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        pecas_formset = context['pecas_formset']
        servicos_formset = context['servicos_formset']

        banco = get_licenca_db_config(self.request) or 'default'

        logger.debug("[OsUpdateView] Form valid=%s Pecas valid=%s Servicos valid=%s", form.is_valid(), pecas_formset.is_valid(), servicos_formset.is_valid())
        if form.is_valid() and pecas_formset.is_valid() and servicos_formset.is_valid():
            try:
                os_obj = self.object
                os_updates = form.cleaned_data.copy()
                os_updates.pop('os_topr', None)

                # Converter entidades em IDs
                if hasattr(os_updates.get('os_clie'), 'enti_clie'):
                    os_updates['os_clie'] = os_updates['os_clie'].enti_clie
                if hasattr(os_updates.get('os_resp'), 'enti_clie'):
                    os_updates['os_resp'] = os_updates['os_resp'].enti_clie

                pecas_data = []
                for item_form in pecas_formset.forms:
                    if not item_form.cleaned_data or item_form.cleaned_data.get('DELETE'):
                        continue
                    item = item_form.cleaned_data.copy()
                    prod = item.get('peca_prod')
                    prod_code = getattr(prod, 'prod_codi', prod)
                    pecas_data.append({
                        'peca_prod': prod_code,
                        'peca_quan': item.get('peca_quan', 1),
                        'peca_unit': item.get('peca_unit', 0),
                        'peca_desc': item.get('peca_desc', 0),
                    })

                servicos_data = []
                for item_form in servicos_formset.forms:
                    if not item_form.cleaned_data or item_form.cleaned_data.get('DELETE'):
                        continue
                    item = item_form.cleaned_data.copy()
                    prod = item.get('serv_prod')
                    prod_code = getattr(prod, 'prod_codi', prod)
                    servicos_data.append({
                        'serv_prod': prod_code,
                        'serv_quan': item.get('serv_quan', 1),
                        'serv_unit': item.get('serv_unit', 0),
                        'serv_desc': item.get('serv_desc', 0),
                    })

                if not pecas_data and not servicos_data:
                    messages.error(self.request, "A OS precisa ter pelo menos uma peça ou serviço.")
                    return self.form_invalid(form)

                OsService.update_os(banco, os_obj, os_updates, pecas_data, servicos_data)
                logger.debug(
                    "[OsUpdateView] OS atualizada os_os=%s os_desc=%s os_tota=%s",
                    getattr(os_obj, 'os_os', None), getattr(os_obj, 'os_desc', None), getattr(os_obj, 'os_tota', None)
                )
                messages.success(self.request, f"OS {os_obj.os_os} atualizada com sucesso.")
                return redirect(self.get_success_url())
            except Exception as e:
                messages.error(self.request, f"Erro ao atualizar OS: {str(e)}")
                import traceback
                logger.exception("[OsUpdateView] Falha ao atualizar OS: %s", e)
                traceback.print_exc()
                return self.form_invalid(form)
        else:
            if not form.is_valid():
                logger.error("[OsUpdateView] Erros no form: %s", form.errors)
                messages.error(self.request, f"Erros no formulário: {form.errors}")
            if not pecas_formset.is_valid() or not servicos_formset.is_valid():
                logger.error("[OsUpdateView] Erros nos formsets: %s | %s", pecas_formset.errors, servicos_formset.errors)
                messages.error(self.request, "Erros nos itens: verifique peças e serviços.")
            return self.form_invalid(form)