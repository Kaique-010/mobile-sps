from django.views.generic import CreateView
from django.http import JsonResponse
from django.db.models import Subquery, OuterRef, BigIntegerField
from django.db.models.functions import Cast
from django.shortcuts import redirect
from ...models import EntradaEstoque
from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug
from ..forms import EntradaEstoqueForm
import logging
logger = logging.getLogger(__name__)



class EntradaCreateView(CreateView):
    model = EntradaEstoque
    form_class = EntradaEstoqueForm
    template_name = 'Entradas/entradas_criar.html'


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
        
        context['slug'] = self.kwargs.get('slug') or get_licenca_slug()
        return context

    def form_valid(self, form):
        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)
        banco = get_licenca_db_config(self.request) or 'default'

        try:
            from django.db import models
            obj = form.save(commit=False)
            obj.entr_empr = empresa_id
            obj.entr_fili = filial_id
            max_sequ = EntradaEstoque.objects.using(banco).aggregate(
                models.Max('entr_sequ')
            )['entr_sequ__max'] or 0
            obj.entr_sequ = (max_sequ + 1)
            obj.save(using=banco)
            return redirect(self.get_success_url())
        except Exception as e:
            logger.error(f"Erro ao salvar entrada: {e}")
            return self.form_invalid(form)
