from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import CreateView
from django.db import IntegrityError

from ...models import Ordemproducao
from ...services import OrdemProducaoService
from ..forms import OrdemproducaoForm
from .base import OrdemProducaoWebMixin


class OrdemproducaoCreateView(OrdemProducaoWebMixin, CreateView):
    model = Ordemproducao
    form_class = OrdemproducaoForm
    template_name = 'OrdemProducao/ordemproducao_form.html'

    def form_valid(self, form):
        empresa_id = int(self.request.session.get('empresa_id') or 1)
        filial_id = int(self.request.session.get('filial_id') or 1)
        banco = self.get_banco()

        self.object = form.save(commit=False)
        self.object.orpr_empr = empresa_id
        self.object.orpr_fili = filial_id
        if not self.object.orpr_codi:
            self.object.orpr_codi = OrdemProducaoService.proxima_ordem(using=banco, empresa=empresa_id, filial=filial_id)
        for _ in range(5):
            try:
                self.object.save(using=banco)
                break
            except IntegrityError:
                self.object.orpr_codi = OrdemProducaoService.proxima_ordem(using=banco, empresa=empresa_id, filial=filial_id)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('ordem_producao_web:ordemproducao_list', kwargs={'slug': self.get_slug()})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cliente_nome'] = ''
        context['vendedor_nome'] = ''
        context['produto_nome'] = ''
        return context
