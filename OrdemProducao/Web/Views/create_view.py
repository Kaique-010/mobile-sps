from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import CreateView

from ...models import Ordemproducao
from ..forms import OrdemproducaoForm
from .base import OrdemProducaoWebMixin


class OrdemproducaoCreateView(OrdemProducaoWebMixin, CreateView):
    model = Ordemproducao
    form_class = OrdemproducaoForm
    template_name = 'OrdemProducao/ordemproducao_form.html'

    def form_valid(self, form):
        empresa_id = int(self.request.session.get('empresa_id') or 1)
        filial_id = int(self.request.session.get('filial_id') or 1)

        self.object = form.save(commit=False)
        self.object.orpr_empr = empresa_id
        self.object.orpr_fili = filial_id
        self.object.save(using=self.get_banco())
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('ordem_producao_web:ordemproducao_list', kwargs={'slug': self.get_slug()})
