from django.views.generic import CreateView
from django.shortcuts import redirect
from Saidas_Estoque.models import SaidasEstoque
from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug
from ..forms import SaidasEstoqueForm
import logging
logger = logging.getLogger(__name__)


class SaidaCreateView(CreateView):
    model = SaidasEstoque
    form_class = SaidasEstoqueForm
    template_name = 'Saidas/saidas_criar.html'

    def get_success_url(self):
        slug = self.kwargs.get('slug')
        return f"/web/{slug}/saidas/" if slug else "/web/home/"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['database'] = get_licenca_db_config(self.request) or 'default'
        kwargs['empresa_id'] = self.request.session.get('empresa_id', 1)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)
        try:
            from Produtos.models import Produtos
            qs = Produtos.objects.using(banco).all()
            if empresa_id:
                qs = qs.filter(prod_empr=str(empresa_id))
            context['produtos'] = qs.order_by('prod_nome')[:500]
        except Exception as e:
            logger.error(f"Erro ao carregar produtos: {e}")
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
            unit = form.cleaned_data.get('valor_unitario')
            if unit is not None and obj.said_quan is not None:
                obj.said_tota = obj.said_quan * unit
            obj.said_empr = empresa_id
            obj.said_fili = filial_id
            max_sequ = SaidasEstoque.objects.using(banco).aggregate(
                models.Max('said_sequ')
            )['said_sequ__max'] or 0
            obj.said_sequ = (max_sequ + 1)
            obj.save(using=banco)
            return redirect(self.get_success_url())
        except Exception as e:
            logger.error(f"Erro ao salvar saída: {e}")
            return self.form_invalid(form)