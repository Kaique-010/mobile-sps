from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.http import HttpResponse, Http404
from django.contrib import messages

from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug
from django.db.models import Subquery, OuterRef, DecimalField, Value as V, IntegerField
from django.db.models.functions import Coalesce, Cast

from .models import Produtos, Tabelaprecos, SaldoProduto
from .forms import ProdutosForm, TabelaprecosFormSet


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
        formset = TabelaprecosFormSet(self.request.POST, queryset=Tabelaprecos.objects.none(), prefix='precos')
        if formset.is_valid():
            objetos = formset.save(commit=False)
            for obj in objetos:
                # Garantir vínculo pelo código do produto e empresa
                obj.tabe_prod = instance.prod_codi
                try:
                    obj.tabe_empr = int(instance.prod_empr)
                except Exception:
                    pass
                obj.save(using=self.db_alias)
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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        # Carregar preços vinculados ao produto via tabe_prod/tabe_empr
        produto = self.object
        qs = Tabelaprecos.objects.using(self.db_alias).filter(
            tabe_prod=produto.prod_codi,
            tabe_empr=produto.prod_empr
        )
        formset = TabelaprecosFormSet(self.request.POST or None, queryset=qs, prefix='precos')
        # Injetar valores iniciais manualmente, pois não há FK direta
        if not formset.is_bound:
            for i, preco in enumerate(qs):
                try:
                    formset.forms[i].initial = {
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
                    }
                except IndexError:
                    break
        ctx['formset'] = formset
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
        formset = TabelaprecosFormSet(self.request.POST, queryset=Tabelaprecos.objects.using(self.db_alias).filter(
            tabe_prod=form.instance.prod_codi,
            tabe_empr=form.instance.prod_empr
        ), prefix='precos')
        if formset.is_valid():
            objetos = formset.save(commit=False)
            for obj in objetos:
                obj.tabe_prod = instance.prod_codi
                try:
                    obj.tabe_empr = int(instance.prod_empr)
                except Exception:
                    pass
                obj.save(using=self.db_alias)
        messages.success(self.request, f'Produto atualizado com sucesso. Código: {instance.prod_codi}')
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