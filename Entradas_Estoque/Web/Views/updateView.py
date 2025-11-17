from django.views.generic import  UpdateView
import logging
from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug
from django.shortcuts import redirect
logger = logging.getLogger(__name__)
from ...models import EntradaEstoque
from ..forms import EntradaEstoqueForm



class EntradaUpdateView(UpdateView):
    model = EntradaEstoque
    form_class = EntradaEstoqueForm
    template_name = 'Entradas/entradas_criar.html'

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
        context['slug'] = self.kwargs.get('slug') or get_licenca_slug()
        return context

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        try:
            obj = form.save(commit=False)
            obj.save(using=banco)
            return redirect(self.get_success_url())
        except Exception as e:
            logger.error(f"Erro ao atualizar entrada: {e}")
            return self.form_invalid(form)
