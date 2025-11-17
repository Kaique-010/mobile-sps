from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from urllib.parse import quote_plus
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.http import HttpResponse, Http404
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)

from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug
from django.db.models import Subquery, OuterRef, DecimalField, Value as V, IntegerField
from django.db.models.functions import Coalesce, Cast

from .models import (
    Produtos,
    Tabelaprecos,
    SaldoProduto,
    Tabelaprecoshist,
    GrupoProduto,
    SubgrupoProduto,
    FamiliaProduto,
    Marca,
)
from django.utils import timezone
from .forms import (
    ProdutosForm,
    TabelaprecosFormSet,
    TabelaprecosPlainFormSet,
    GrupoForm,
    SubgrupoForm,
    FamiliaForm,
    MarcaForm,
)


class DBAndSlugMixin:
    template_folder = 'templates_spsWeb/Produtos'

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug') or get_licenca_slug()
        self.db_alias = get_licenca_db_config(request)
        if not self.db_alias:
            raise Http404("Banco de dados da licença não encontrado")
        # Capturar empresa/filial priorizando sessão; fallback para headers e querystring
        self.empresa_id = (
            request.session.get('empresa_id')
            or request.headers.get('X-Empresa')
            or request.GET.get('prod_empr')
        )
        self.filial_id = (
            request.session.get('filial_id')
            or request.headers.get('X-Filial')
            or request.GET.get('prod_fili')
        )
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        # Fallback para slug da licença caso esteja vazio
        return reverse_lazy('produtos_web', kwargs={'slug': self.slug or get_licenca_slug()})


class ProdutoListView(DBAndSlugMixin, ListView):
    model = Produtos
    template_name = 'Produtos/produtos_lista.html'
    context_object_name = 'produtos'
    paginate_by = 20

    def get_queryset(self):
        qs = Produtos.objects.using(self.db_alias).all()
        # Filtrar por empresa se disponível para evitar duplicidades entre empresas
        if self.empresa_id:
            qs = qs.filter(prod_empr=str(self.empresa_id))
        prod_nome = (self.request.GET.get('prod_nome') or '').strip()
        prod_codi = (self.request.GET.get('prod_codi') or '').strip()
        if prod_nome:
            qs = qs.filter(prod_nome__icontains=prod_nome)
        if prod_codi:
            qs = qs.filter(prod_codi__icontains=prod_codi)
        # Anotar saldo de estoque via subquery (por empresa/filial quando disponíveis)
        saldo_qs = SaldoProduto.objects.using(self.db_alias).filter(
            produto_codigo=OuterRef('pk')
        )
        if self.empresa_id:
            saldo_qs = saldo_qs.filter(empresa=str(self.empresa_id))
        if self.filial_id:
            saldo_qs = saldo_qs.filter(filial=str(self.filial_id))
        saldo_sub = Subquery(saldo_qs.values('saldo_estoque')[:1], output_field=DecimalField())
        qs = qs.annotate(saldo_estoque=Coalesce(saldo_sub, V(0), output_field=DecimalField()))

        # Anotar preços principais (vista, prazo, custo) por empresa quando disponível
        preco_qs = Tabelaprecos.objects.using(self.db_alias).filter(
            tabe_prod=OuterRef('prod_codi')
        )
        if self.empresa_id:
            try:
                emp_int = int(self.empresa_id)
                preco_qs = preco_qs.filter(tabe_empr=emp_int)
            except Exception:
                pass
        preco_vista_sub = Subquery(preco_qs.values('tabe_avis')[:1], output_field=DecimalField())
        preco_prazo_sub = Subquery(preco_qs.values('tabe_praz')[:1], output_field=DecimalField())
        preco_custo_sub = Subquery(preco_qs.values('tabe_cust')[:1], output_field=DecimalField())
        qs = qs.annotate(
            preco_vista=preco_vista_sub,
            preco_prazo=preco_prazo_sub,
            preco_custo=preco_custo_sub,
        )
        return qs.order_by('prod_empr', 'prod_codi')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        ctx['prod_nome'] = (self.request.GET.get('prod_nome') or '').strip()
        ctx['prod_codi'] = (self.request.GET.get('prod_codi') or '').strip()
        # Preservar filtros na paginação
        extra_parts = []
        if ctx['prod_nome']:
            extra_parts.append('&prod_nome=' + quote_plus(ctx['prod_nome']))
        if ctx['prod_codi']:
            extra_parts.append('&prod_codi=' + quote_plus(ctx['prod_codi']))
        ctx['extra_query'] = ''.join(extra_parts)
        # Popular pseudo-relacionamento de preços para o template existente (tabelaprecos_set.all)
        class _ManagerLike:
            def __init__(self, items):
                self._items = items
            def all(self):
                return self._items

        try:
            emp_int = int(self.empresa_id) if self.empresa_id else None
        except Exception:
            emp_int = None

        produtos = ctx.get('page_obj').object_list if ctx.get('page_obj') else ctx.get('produtos', [])
        for p in produtos:
            precos_qs = Tabelaprecos.objects.using(self.db_alias).filter(tabe_prod=p.prod_codi)
            if emp_int is not None:
                precos_qs = precos_qs.filter(tabe_empr=emp_int)
            p.tabelaprecos_set = _ManagerLike(list(precos_qs))
        return ctx


class ProdutoCreateView(DBAndSlugMixin, CreateView):
    model = Produtos
    form_class = ProdutosForm
    template_name = 'Produtos/produtos_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        # Formset vazio por enquanto; será inicializado após salvar o produto
        from .models import Tabelaprecos
        ctx['formset'] = TabelaprecosFormSet(queryset=Tabelaprecos.objects.none(), prefix='precos')
        return ctx

    def form_valid(self, form):
        instance = form.save(commit=False)
        # Atribuir empresa a partir de headers ou sessão
        empresa = (
            self.request.headers.get('X-Empresa')
            or self.request.META.get('HTTP_X_EMPRESA')
            or self.request.session.get('empresa_id')
            or self.empresa_id
        )
        if not empresa:
            form.add_error(None, 'Empresa não informada nos headers ou sessão.')
            return self.form_invalid(form)
        instance.prod_empr = str(empresa)
        # Garantir origem de mercadoria padrão como no serializer
        try:
            instance.prod_orig_merc = '0'
        except Exception:
            pass
        # Remover espaços e gerar código sequencial quando vazio
        if instance.prod_codi:
            instance.prod_codi = str(instance.prod_codi).strip()
        if not instance.prod_codi:
            # Geração sequencial por empresa, sem zeros à esquerda, evitando colisão
            ultimo = Produtos.objects.using(self.db_alias).filter(
                prod_empr=str(empresa)
            ).order_by('-prod_codi').first()
            proximo = int(ultimo.prod_codi) + 1 if (ultimo and str(ultimo.prod_codi).isdigit()) else 1
            while Produtos.objects.using(self.db_alias).filter(
                prod_empr=str(empresa), prod_codi=str(proximo)
            ).exists():
                proximo += 1
            instance.prod_codi = str(proximo)
        # Sincronizar prod_codi_nume quando disponível
        if hasattr(instance, 'prod_codi_nume'):
            instance.prod_codi_nume = instance.prod_codi
        # Tratar upload de foto (FileField externo ao ModelForm)
        uploaded = self.request.FILES.get('prod_foto') or form.cleaned_data.get('prod_foto')
        if uploaded:
            try:
                instance.prod_foto = uploaded.read()
            except Exception:
                pass
        instance.save(using=self.db_alias)

        # Salvar preços (se enviados)
        formset = TabelaprecosPlainFormSet(self.request.POST, prefix='precos')
        if not formset.is_valid():
            for fs_form in formset.forms:
                for field, errs in fs_form.errors.items():
                    for err in errs:
                        messages.error(self.request, f'Preço - erro em {field}: {err}')
            ctx = self.get_context_data()
            ctx['form'] = form
            ctx['formset'] = formset
            return self.render_to_response(ctx)
        for f in formset.forms:
            if not f.cleaned_data:
                continue
            cd = f.cleaned_data
            tabe_prod = instance.prod_codi
            try:
                tabe_empr = int(instance.prod_empr)
            except Exception:
                tabe_empr = instance.prod_empr
            try:
                tabe_fili = int(self.filial_id) if self.filial_id else 1
            except Exception:
                tabe_fili = 1

            existing = Tabelaprecos.objects.using(self.db_alias).filter(
                tabe_empr=tabe_empr,
                tabe_fili=tabe_fili,
                tabe_prod=tabe_prod,
            ).first()

            if existing:
                historico = "Alteração de preços via Web"
                if cd.get('tabe_prco') is not None and existing.tabe_prco != cd.get('tabe_prco'):
                    historico += f"\nPreço Normal: R$ {float(existing.tabe_prco or 0):.2f} -> R$ {float(cd.get('tabe_prco') or 0):.2f}"
                if cd.get('tabe_avis') is not None and existing.tabe_avis != cd.get('tabe_avis'):
                    historico += f"\nPreço à Vista: R$ {float(existing.tabe_avis or 0):.2f} -> R$ {float(cd.get('tabe_avis') or 0):.2f}"
                if cd.get('tabe_apra') is not None and existing.tabe_apra != cd.get('tabe_apra'):
                    historico += f"\nPreço a Prazo: R$ {float(existing.tabe_apra or 0):.2f} -> R$ {float(cd.get('tabe_apra') or 0):.2f}"

                hist_data = {
                    'tabe_empr': tabe_empr,
                    'tabe_fili': tabe_fili,
                    'tabe_prod': tabe_prod,
                    'tabe_data_hora': timezone.now(),
                    'tabe_hist': historico,
                    'tabe_perc_reaj': cd.get('tabe_perc_reaj'),
                    'tabe_prco_ante': existing.tabe_prco,
                    'tabe_avis_ante': existing.tabe_avis,
                    'tabe_apra_ante': existing.tabe_apra,
                    'tabe_pipi_ante': getattr(existing, 'tabe_pipi', None),
                    'tabe_fret_ante': getattr(existing, 'tabe_fret', None),
                    'tabe_desp_ante': getattr(existing, 'tabe_desp', None),
                    'tabe_cust_ante': getattr(existing, 'tabe_cust', None),
                    'tabe_cuge_ante': getattr(existing, 'tabe_cuge', None),
                    'tabe_icms_ante': getattr(existing, 'tabe_icms', None),
                    'tabe_impo_ante': getattr(existing, 'tabe_impo', None),
                    'tabe_marg_ante': getattr(existing, 'tabe_marg', None),
                    'tabe_praz_ante': getattr(existing, 'tabe_praz', None),
                    'tabe_valo_st_ante': getattr(existing, 'tabe_valo_st', None),
                    'tabe_prco_novo': cd.get('tabe_prco'),
                    'tabe_avis_novo': cd.get('tabe_avis'),
                    'tabe_apra_novo': cd.get('tabe_apra'),
                    'tabe_pipi_novo': cd.get('tabe_pipi'),
                    'tabe_fret_novo': cd.get('tabe_fret'),
                    'tabe_desp_novo': cd.get('tabe_desp'),
                    'tabe_cust_novo': cd.get('tabe_cust'),
                    'tabe_cuge_novo': cd.get('tabe_cuge'),
                    'tabe_icms_novo': cd.get('tabe_icms'),
                    'tabe_impo_novo': cd.get('tabe_impo'),
                    'tabe_marg_novo': cd.get('tabe_marg'),
                    'tabe_praz_novo': cd.get('tabe_praz'),
                    'tabe_valo_st_novo': cd.get('tabe_valo_st'),
                }
                Tabelaprecoshist.objects.using(self.db_alias).create(**hist_data)
                Tabelaprecos.objects.using(self.db_alias).filter(
                    tabe_empr=tabe_empr,
                    tabe_fili=tabe_fili,
                    tabe_prod=tabe_prod,
                ).update(
                    tabe_prco=cd.get('tabe_prco'),
                    tabe_icms=cd.get('tabe_icms'),
                    tabe_desc=cd.get('tabe_desc'),
                    tabe_vipi=cd.get('tabe_vipi'),
                    tabe_pipi=cd.get('tabe_pipi'),
                    tabe_fret=cd.get('tabe_fret'),
                    tabe_desp=cd.get('tabe_desp'),
                    tabe_cust=cd.get('tabe_cust'),
                    tabe_marg=cd.get('tabe_marg'),
                    tabe_impo=cd.get('tabe_impo'),
                    tabe_avis=cd.get('tabe_avis'),
                    tabe_praz=cd.get('tabe_praz'),
                    tabe_apra=cd.get('tabe_apra'),
                    tabe_vare=cd.get('tabe_vare'),
                    field_log_data=cd.get('field_log_data'),
                    field_log_time=cd.get('field_log_time'),
                    tabe_valo_st=cd.get('tabe_valo_st'),
                    tabe_perc_reaj=cd.get('tabe_perc_reaj'),
                    tabe_hist=cd.get('tabe_hist'),
                    tabe_cuge=cd.get('tabe_cuge'),
                    tabe_entr=cd.get('tabe_entr'),
                    tabe_perc_st=cd.get('tabe_perc_st'),
                )
            else:
                hist_data = {
                    'tabe_empr': tabe_empr,
                    'tabe_fili': tabe_fili,
                    'tabe_prod': tabe_prod,
                    'tabe_data_hora': timezone.now(),
                    'tabe_hist': "Criação de preços via Web",
                    'tabe_perc_reaj': cd.get('tabe_perc_reaj'),
                    'tabe_prco_novo': cd.get('tabe_prco'),
                    'tabe_avis_novo': cd.get('tabe_avis'),
                    'tabe_apra_novo': cd.get('tabe_apra'),
                }
                Tabelaprecoshist.objects.using(self.db_alias).create(**hist_data)
                Tabelaprecos.objects.using(self.db_alias).create(
                    tabe_empr=tabe_empr,
                    tabe_fili=tabe_fili,
                    tabe_prod=tabe_prod,
                    tabe_prco=cd.get('tabe_prco'),
                    tabe_icms=cd.get('tabe_icms'),
                    tabe_desc=cd.get('tabe_desc'),
                    tabe_vipi=cd.get('tabe_vipi'),
                    tabe_pipi=cd.get('tabe_pipi'),
                    tabe_fret=cd.get('tabe_fret'),
                    tabe_desp=cd.get('tabe_desp'),
                    tabe_cust=cd.get('tabe_cust'),
                    tabe_marg=cd.get('tabe_marg'),
                    tabe_impo=cd.get('tabe_impo'),
                    tabe_avis=cd.get('tabe_avis'),
                    tabe_praz=cd.get('tabe_praz'),
                    tabe_apra=cd.get('tabe_apra'),
                    tabe_vare=cd.get('tabe_vare'),
                    field_log_data=cd.get('field_log_data'),
                    field_log_time=cd.get('field_log_time'),
                    tabe_valo_st=cd.get('tabe_valo_st'),
                    tabe_perc_reaj=cd.get('tabe_perc_reaj'),
                    tabe_hist=cd.get('tabe_hist'),
                    tabe_cuge=cd.get('tabe_cuge'),
                    tabe_entr=cd.get('tabe_entr'),
                    tabe_perc_st=cd.get('tabe_perc_st'),
                )
        messages.success(self.request, f'Produto criado com sucesso. Código: {instance.prod_codi}')
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        # Consolidar erros do formulário principal em mensagens para o usuário
        if form.errors:
            for field, errs in form.errors.items():
                for err in errs:
                    if field == '__all__':
                        messages.error(self.request, f'{err}')
                    else:
                        messages.error(self.request, f'Erro em {field}: {err}')
        # Também validar o formset de preços, se presente na requisição
        from .models import Tabelaprecos
        try:
            formset = TabelaprecosFormSet(self.request.POST, queryset=Tabelaprecos.objects.none(), prefix='precos')
            if not formset.is_valid():
                for fs_form in formset.forms:
                    if fs_form.errors:
                        for field, errs in fs_form.errors.items():
                            for err in errs:
                                messages.error(self.request, f'Preço - erro em {field}: {err}')
        except Exception:
            pass
        return super().form_invalid(form)


class ProdutoUpdateView(DBAndSlugMixin, UpdateView):
    model = Produtos
    form_class = ProdutosForm
    template_name = 'Produtos/produtos_update.html'
    pk_url_kwarg = 'prod_codi'
    slug_url_kwarg = 'slug'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Não permitir alterar o PK no update para evitar INSERT acidental
        if 'prod_codi' in form.fields:
            form.fields['prod_codi'].disabled = True
            form.fields['prod_codi'].required = False
        return form

    def get_object(self, queryset=None):
        prod_codi = self.kwargs.get('prod_codi')
        if not prod_codi:
            raise Http404('Código do produto não informado')
        # Buscar por código e, se informado, por empresa para evitar múltiplos resultados
        qs = Produtos.objects.using(self.db_alias).filter(prod_codi=prod_codi)
        if self.empresa_id:
            qs = qs.filter(prod_empr=str(self.empresa_id))
        obj = qs.order_by('prod_empr').first()
        if not obj:
            raise Http404('Produto não encontrado')
        return obj

# Grupos
class GrupoListView(DBAndSlugMixin, ListView):
    model = GrupoProduto
    template_name = 'Produtos/grupos_list.html'
    context_object_name = 'grupos'
    paginate_by = 20

    def get_queryset(self):
        qs = GrupoProduto.objects.using(self.db_alias).all()
        nome = (self.request.GET.get('nome') or '').strip()
        if nome:
            qs = qs.filter(descricao__icontains=nome)
        return qs.order_by('codigo')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        ctx['nome'] = (self.request.GET.get('nome') or '').strip()
        return ctx

class GrupoCreateView(DBAndSlugMixin, CreateView):
    model = GrupoProduto
    form_class = GrupoForm
    template_name = 'Produtos/grupo_create.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.save(using=self.db_alias)
        messages.success(self.request, 'Grupo criado com sucesso.')
        return redirect(self.get_success_url())

class GrupoUpdateView(DBAndSlugMixin, UpdateView):
    model = GrupoProduto
    form_class = GrupoForm
    template_name = 'Produtos/grupo_update.html'
    pk_url_kwarg = 'codigo'

    def get_queryset(self):
        return GrupoProduto.objects.using(self.db_alias).all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.save(using=self.db_alias)
        messages.success(self.request, 'Grupo atualizado com sucesso.')
        return redirect(self.get_success_url())

class GrupoDeleteView(DBAndSlugMixin, DeleteView):
    model = GrupoProduto
    template_name = 'Produtos/grupo_delete.html'
    pk_url_kwarg = 'codigo'

    def get_queryset(self):
        return GrupoProduto.objects.using(self.db_alias).all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        return ctx

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete(using=self.db_alias)
        messages.success(self.request, 'Grupo excluído com sucesso.')
        return redirect(self.get_success_url())

# Subgrupos
class SubgrupoListView(DBAndSlugMixin, ListView):
    model = SubgrupoProduto
    template_name = 'Produtos/subgrupos_list.html'
    context_object_name = 'subgrupos'
    paginate_by = 20

    def get_queryset(self):
        qs = SubgrupoProduto.objects.using(self.db_alias).all()
        nome = (self.request.GET.get('nome') or '').strip()
        if nome:
            qs = qs.filter(descricao__icontains=nome)
        return qs.order_by('codigo')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        ctx['nome'] = (self.request.GET.get('nome') or '').strip()
        return ctx

class SubgrupoCreateView(DBAndSlugMixin, CreateView):
    model = SubgrupoProduto
    form_class = SubgrupoForm
    template_name = 'Produtos/subgrupo_create.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.save(using=self.db_alias)
        messages.success(self.request, 'Subgrupo criado com sucesso.')
        return redirect(self.get_success_url())

class SubgrupoUpdateView(DBAndSlugMixin, UpdateView):
    model = SubgrupoProduto
    form_class = SubgrupoForm
    template_name = 'Produtos/subgrupo_update.html'
    pk_url_kwarg = 'codigo'

    def get_queryset(self):
        return SubgrupoProduto.objects.using(self.db_alias).all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.save(using=self.db_alias)
        messages.success(self.request, 'Subgrupo atualizado com sucesso.')
        return redirect(self.get_success_url())

class SubgrupoDeleteView(DBAndSlugMixin, DeleteView):
    model = SubgrupoProduto
    template_name = 'Produtos/subgrupo_delete.html'
    pk_url_kwarg = 'codigo'

    def get_queryset(self):
        return SubgrupoProduto.objects.using(self.db_alias).all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        return ctx

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete(using=self.db_alias)
        messages.success(self.request, 'Subgrupo excluído com sucesso.')
        return redirect(self.get_success_url())

# Famílias
class FamiliaListView(DBAndSlugMixin, ListView):
    model = FamiliaProduto
    template_name = 'Produtos/familias_produto_list.html'
    context_object_name = 'familias'
    paginate_by = 20

    def get_queryset(self):
        qs = FamiliaProduto.objects.using(self.db_alias).all()
        nome = (self.request.GET.get('nome') or '').strip()
        if nome:
            qs = qs.filter(descricao__icontains=nome)
        return qs.order_by('codigo')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        ctx['nome'] = (self.request.GET.get('nome') or '').strip()
        return ctx

class FamiliaCreateView(DBAndSlugMixin, CreateView):
    model = FamiliaProduto
    form_class = FamiliaForm
    template_name = 'Produtos/familia_produto_create.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.save(using=self.db_alias)
        messages.success(self.request, 'Família criada com sucesso.')
        return redirect(self.get_success_url())

class FamiliaUpdateView(DBAndSlugMixin, UpdateView):
    model = FamiliaProduto
    form_class = FamiliaForm
    template_name = 'Produtos/familia_produto_update.html'
    pk_url_kwarg = 'codigo'

    def get_queryset(self):
        return FamiliaProduto.objects.using(self.db_alias).all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.save(using=self.db_alias)
        messages.success(self.request, 'Família atualizada com sucesso.')
        return redirect(self.get_success_url())

class FamiliaDeleteView(DBAndSlugMixin, DeleteView):
    model = FamiliaProduto
    template_name = 'Produtos/familia_produto_delete.html'
    pk_url_kwarg = 'codigo'

    def get_queryset(self):
        return FamiliaProduto.objects.using(self.db_alias).all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        return ctx

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete(using=self.db_alias)
        messages.success(self.request, 'Família excluída com sucesso.')
        return redirect(self.get_success_url())

# Marcas
class MarcaListViewWeb(DBAndSlugMixin, ListView):
    model = Marca
    template_name = 'Produtos/marcas_list.html'
    context_object_name = 'marcas'
    paginate_by = 20

    def get_queryset(self):
        qs = Marca.objects.using(self.db_alias).all()
        nome = (self.request.GET.get('nome') or '').strip()
        if nome:
            qs = qs.filter(nome__icontains=nome)
        return qs.order_by('codigo')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        ctx['nome'] = (self.request.GET.get('nome') or '').strip()
        return ctx

class MarcaCreateView(DBAndSlugMixin, CreateView):
    model = Marca
    form_class = MarcaForm
    template_name = 'Produtos/marca_create.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.save(using=self.db_alias)
        messages.success(self.request, 'Marca criada com sucesso.')
        return redirect(self.get_success_url())

class MarcaUpdateView(DBAndSlugMixin, UpdateView):
    model = Marca
    form_class = MarcaForm
    template_name = 'Produtos/marca_update.html'
    pk_url_kwarg = 'codigo'

    def get_queryset(self):
        return Marca.objects.using(self.db_alias).all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.save(using=self.db_alias)
        messages.success(self.request, 'Marca atualizada com sucesso.')
        return redirect(self.get_success_url())

class MarcaDeleteView(DBAndSlugMixin, DeleteView):
    model = Marca
    template_name = 'Produtos/marca_delete.html'
    pk_url_kwarg = 'codigo'

    def get_queryset(self):
        return Marca.objects.using(self.db_alias).all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        return ctx

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete(using=self.db_alias)
        messages.success(self.request, 'Marca excluída com sucesso.')
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        # Carregar preços vinculados ao produto via tabe_prod/tabe_empr
        produto = self.object
        try:
            emp_int = int(produto.prod_empr)
        except Exception:
            emp_int = produto.prod_empr
        qs = Tabelaprecos.objects.using(self.db_alias).filter(
            tabe_prod=produto.prod_codi,
            tabe_empr=emp_int
        )
        initial_list = []
        for preco in qs:
            initial_list.append({
                'tabe_fili': preco.tabe_fili,
                'tabe_prco': preco.tabe_prco,
                'tabe_icms': preco.tabe_icms,
                'tabe_desc': preco.tabe_desc,
                'tabe_vipi': preco.tabe_vipi,
                'tabe_pipi': preco.tabe_pipi,
                'tabe_fret': preco.tabe_fret,
                'tabe_desp': preco.tabe_desp,
                'tabe_cust': preco.tabe_cust,
                'tabe_marg': preco.tabe_marg,
                'tabe_impo': preco.tabe_impo,
                'tabe_avis': preco.tabe_avis,
                'tabe_praz': preco.tabe_praz,
                'tabe_apra': preco.tabe_apra,
                'tabe_vare': getattr(preco, 'tabe_vare', None),
                'tabe_hist': getattr(preco, 'tabe_hist', None),
                'tabe_cuge': getattr(preco, 'tabe_cuge', None),
                'tabe_entr': getattr(preco, 'tabe_entr', None),
                'tabe_perc_st': getattr(preco, 'tabe_perc_st', None),
            })
        ctx['formset'] = TabelaprecosPlainFormSet(initial=initial_list, prefix='precos')
        logger.info(f'Preços carregados para produto {produto.prod_codi}: {initial_list}')
        return ctx

    def form_valid(self, form):
        instance = form.save(commit=False)
        # Garantir que o código (PK) permaneça o mesmo do objeto carregado
        instance.prod_codi = form.instance.prod_codi
        # Manter/atualizar empresa a partir de headers ou sessão, quando presente
        empresa = (
            self.request.headers.get('X-Empresa')
            or self.request.META.get('HTTP_X_EMPRESA')
            or self.request.session.get('empresa_id')
            or self.empresa_id
        )
        if empresa:
            instance.prod_empr = str(empresa)
        # Tratar upload de foto (FileField externo ao ModelForm)
        uploaded = self.request.FILES.get('prod_foto') or form.cleaned_data.get('prod_foto')
        if uploaded:
            try:
                instance.prod_foto = uploaded.read()
            except Exception:
                pass
        instance.save(using=self.db_alias)

        # Atualizar preços
        try:
            emp_int = int(form.instance.prod_empr)
        except Exception:
            emp_int = form.instance.prod_empr
        formset = TabelaprecosPlainFormSet(self.request.POST, prefix='precos')
        if not formset.is_valid():
            for fs_form in formset.forms:
                for field, errs in fs_form.errors.items():
                    for err in errs:
                        messages.error(self.request, f'Preço - erro em {field}: {err}')
            ctx = self.get_context_data()
            ctx['form'] = form
            ctx['formset'] = formset
            return self.render_to_response(ctx)
        for f in formset.forms:
            if not f.cleaned_data:
                continue
            cd = f.cleaned_data
            tabe_prod = instance.prod_codi
            try:
                tabe_empr = int(instance.prod_empr)
            except Exception:
                tabe_empr = instance.prod_empr
            try:
                tabe_fili = int(self.filial_id) if self.filial_id else 1
            except Exception:
                tabe_fili = 1

            existing = Tabelaprecos.objects.using(self.db_alias).filter(
                tabe_empr=tabe_empr,
                tabe_fili=tabe_fili,
                tabe_prod=tabe_prod,
            ).first()

            if existing:
                historico = "Alteração de preços via Web"
                if cd.get('tabe_prco') is not None and existing.tabe_prco != cd.get('tabe_prco'):
                    historico += f"\nPreço Normal: R$ {float(existing.tabe_prco or 0):.2f} -> R$ {float(cd.get('tabe_prco') or 0):.2f}"
                if cd.get('tabe_avis') is not None and existing.tabe_avis != cd.get('tabe_avis'):
                    historico += f"\nPreço à Vista: R$ {float(existing.tabe_avis or 0):.2f} -> R$ {float(cd.get('tabe_avis') or 0):.2f}"
                if cd.get('tabe_apra') is not None and existing.tabe_apra != cd.get('tabe_apra'):
                    historico += f"\nPreço a Prazo: R$ {float(existing.tabe_apra or 0):.2f} -> R$ {float(cd.get('tabe_apra') or 0):.2f}"

                hist_data = {
                    'tabe_empr': tabe_empr,
                    'tabe_fili': tabe_fili,
                    'tabe_prod': tabe_prod,
                    'tabe_data_hora': timezone.now(),
                    'tabe_hist': historico,
                    'tabe_perc_reaj': cd.get('tabe_perc_reaj'),
                    'tabe_prco_ante': existing.tabe_prco,
                    'tabe_avis_ante': existing.tabe_avis,
                    'tabe_apra_ante': existing.tabe_apra,
                    'tabe_pipi_ante': getattr(existing, 'tabe_pipi', None),
                    'tabe_fret_ante': getattr(existing, 'tabe_fret', None),
                    'tabe_desp_ante': getattr(existing, 'tabe_desp', None),
                    'tabe_cust_ante': getattr(existing, 'tabe_cust', None),
                    'tabe_cuge_ante': getattr(existing, 'tabe_cuge', None),
                    'tabe_icms_ante': getattr(existing, 'tabe_icms', None),
                    'tabe_impo_ante': getattr(existing, 'tabe_impo', None),
                    'tabe_marg_ante': getattr(existing, 'tabe_marg', None),
                    'tabe_praz_ante': getattr(existing, 'tabe_praz', None),
                    'tabe_valo_st_ante': getattr(existing, 'tabe_valo_st', None),
                    'tabe_prco_novo': cd.get('tabe_prco'),
                    'tabe_avis_novo': cd.get('tabe_avis'),
                    'tabe_apra_novo': cd.get('tabe_apra'),
                    'tabe_pipi_novo': cd.get('tabe_pipi'),
                    'tabe_fret_novo': cd.get('tabe_fret'),
                    'tabe_desp_novo': cd.get('tabe_desp'),
                    'tabe_cust_novo': cd.get('tabe_cust'),
                    'tabe_cuge_novo': cd.get('tabe_cuge'),
                    'tabe_icms_novo': cd.get('tabe_icms'),
                    'tabe_impo_novo': cd.get('tabe_impo'),
                    'tabe_marg_novo': cd.get('tabe_marg'),
                    'tabe_praz_novo': cd.get('tabe_praz'),
                    'tabe_valo_st_novo': cd.get('tabe_valo_st'),
                }
                Tabelaprecoshist.objects.using(self.db_alias).create(**hist_data)
                Tabelaprecos.objects.using(self.db_alias).filter(
                    tabe_empr=tabe_empr,
                    tabe_fili=tabe_fili,
                    tabe_prod=tabe_prod,
                ).update(
                    tabe_prco=cd.get('tabe_prco'),
                    tabe_icms=cd.get('tabe_icms'),
                    tabe_desc=cd.get('tabe_desc'),
                    tabe_vipi=cd.get('tabe_vipi'),
                    tabe_pipi=cd.get('tabe_pipi'),
                    tabe_fret=cd.get('tabe_fret'),
                    tabe_desp=cd.get('tabe_desp'),
                    tabe_cust=cd.get('tabe_cust'),
                    tabe_marg=cd.get('tabe_marg'),
                    tabe_impo=cd.get('tabe_impo'),
                    tabe_avis=cd.get('tabe_avis'),
                    tabe_praz=cd.get('tabe_praz'),
                    tabe_apra=cd.get('tabe_apra'),
                    tabe_vare=cd.get('tabe_vare'),
                    field_log_data=cd.get('field_log_data'),
                    field_log_time=cd.get('field_log_time'),
                    tabe_valo_st=cd.get('tabe_valo_st'),
                    tabe_perc_reaj=cd.get('tabe_perc_reaj'),
                    tabe_hist=cd.get('tabe_hist'),
                    tabe_cuge=cd.get('tabe_cuge'),
                    tabe_entr=cd.get('tabe_entr'),
                    tabe_perc_st=cd.get('tabe_perc_st'),
                )
            else:
                hist_data = {
                    'tabe_empr': tabe_empr,
                    'tabe_fili': tabe_fili,
                    'tabe_prod': tabe_prod,
                    'tabe_data_hora': timezone.now(),
                    'tabe_hist': "Criação de preços via Web",
                    'tabe_perc_reaj': cd.get('tabe_perc_reaj'),
                    'tabe_prco_novo': cd.get('tabe_prco'),
                    'tabe_avis_novo': cd.get('tabe_avis'),
                    'tabe_apra_novo': cd.get('tabe_apra'),
                }
                Tabelaprecoshist.objects.using(self.db_alias).create(**hist_data)
                Tabelaprecos.objects.using(self.db_alias).create(
                    tabe_empr=tabe_empr,
                    tabe_fili=tabe_fili,
                    tabe_prod=tabe_prod,
                    tabe_prco=cd.get('tabe_prco'),
                    tabe_icms=cd.get('tabe_icms'),
                    tabe_desc=cd.get('tabe_desc'),
                    tabe_vipi=cd.get('tabe_vipi'),
                    tabe_pipi=cd.get('tabe_pipi'),
                    tabe_fret=cd.get('tabe_fret'),
                    tabe_desp=cd.get('tabe_desp'),
                    tabe_cust=cd.get('tabe_cust'),
                    tabe_marg=cd.get('tabe_marg'),
                    tabe_impo=cd.get('tabe_impo'),
                    tabe_avis=cd.get('tabe_avis'),
                    tabe_praz=cd.get('tabe_praz'),
                    tabe_apra=cd.get('tabe_apra'),
                    tabe_vare=cd.get('tabe_vare'),
                    field_log_data=cd.get('field_log_data'),
                    field_log_time=cd.get('field_log_time'),
                    tabe_valo_st=cd.get('tabe_valo_st'),
                    tabe_perc_reaj=cd.get('tabe_perc_reaj'),
                    tabe_hist=cd.get('tabe_hist'),
                    tabe_cuge=cd.get('tabe_cuge'),
                    tabe_entr=cd.get('tabe_entr'),
                    tabe_perc_st=cd.get('tabe_perc_st'),
                )
        messages.success(self.request, f'Produto atualizado com sucesso. Código: {instance.prod_codi}')
        logger.info(f'Produto atualizado com sucesso. Código: {instance.prod_codi},tabela de preços atualizada com sucesso.')
        return redirect(self.get_success_url())


class ProdutoDeleteView(DBAndSlugMixin, DeleteView):
    model = Produtos
    template_name = 'Produtos/produto_confirm_delete.html'
    pk_url_kwarg = 'prod_codi'

    def get_object(self, queryset=None):
        prod_codi = self.kwargs.get('prod_codi')
        if not prod_codi:
            raise Http404('Código do produto não informado')
        qs = Produtos.objects.using(self.db_alias).filter(prod_codi=prod_codi)
        if self.empresa_id:
            qs = qs.filter(prod_empr=str(self.empresa_id))
        obj = qs.order_by('prod_empr').first()
        if not obj:
            raise Http404('Produto não encontrado')
        return obj

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.delete(using=self.db_alias)
        messages.success(self.request, 'Produto excluído com sucesso.')
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        return ctx


class ExportarProdutosView(DBAndSlugMixin, View):
    def get(self, request, *args, **kwargs):
        qs = Produtos.objects.using(self.db_alias).all()
        prod_nome = (request.GET.get('prod_nome') or '').strip()
        prod_codi = (request.GET.get('prod_codi') or '').strip()
        if prod_nome:
            qs = qs.filter(prod_nome__icontains=prod_nome)
        if prod_codi:
            qs = qs.filter(prod_codi__icontains=prod_codi)

        # CSV simples
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="produtos.csv"'
        response.write('empresa,codigo,nome,unidade,grupo,subgrupo,familia,marca\n')
        for p in qs.order_by('prod_empr', 'prod_codi'):
            response.write(f"{p.prod_empr},{p.prod_codi},\"{p.prod_nome}\",{getattr(p.prod_unme,'pk', '')},{getattr(p.prod_grup,'pk','')},{getattr(p.prod_sugr,'pk','')},{getattr(p.prod_fami,'pk','')},{getattr(p.prod_marc,'pk','')}\n")
        return response


class ProdutoFotoView(DBAndSlugMixin, View):
    def get(self, request, *args, **kwargs):
        prod_codi = kwargs.get('prod_codi')
        if not prod_codi:
            raise Http404('Código do produto não informado')
        qs = Produtos.objects.using(self.db_alias).filter(prod_codi=prod_codi)
        if self.empresa_id:
            qs = qs.filter(prod_empr=str(self.empresa_id))
        produto = qs.order_by('prod_empr').first()
        if not produto:
            raise Http404('Produto não encontrado')

        foto = produto.prod_foto
        if not foto:
            # Sem foto, retornar 404 para que o template use placeholder
            raise Http404('Foto não disponível')
        return HttpResponse(bytes(foto), content_type='image/jpeg')