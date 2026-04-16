from django.views.generic import CreateView
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib import messages
from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.models import Bombas
from transportes.forms.bombas import BombasForm
from transportes.services.bombas import BombasService

class BombasCreateView(CreateView):
    model = Bombas
    form_class = BombasForm
    template_name = 'transportes/bombas_form.html'

    def get_success_url(self):
        return reverse('transportes:bombas_lista', kwargs={'slug': self.kwargs['slug']})

    def _get_banco(self):
        slug = self.kwargs.get('slug')
        return get_db_from_slug(slug) if slug else get_licenca_db_config(self.request)

    def form_valid(self, form):
        banco = self._get_banco()
        empresa_id = self.request.session.get('empresa_id')
        
        if not empresa_id:
            messages.error(self.request, "Empresa não identificada na sessão. Por favor, faça login novamente.")
            return self.form_invalid(form)

        self.object = BombasService.criar(empresa_id=int(empresa_id), form=form, using=banco)
        
        messages.success(self.request, f'Bomba {self.object.bomb_codi} criada com sucesso!')
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')
        context['titulo'] = 'Nova Bomba'
        context['acao'] = 'Criar'
        return context
