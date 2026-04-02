from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import UpdateView

from ...models import Ordemproducao
from ..forms import OrdemproducaoForm
from .base import OrdemProducaoWebMixin


class OrdemproducaoUpdateView(OrdemProducaoWebMixin, UpdateView):
    model = Ordemproducao
    form_class = OrdemproducaoForm
    template_name = 'OrdemProducao/ordemproducao_form.html'
    pk_url_kwarg = 'orpr_codi'

    def get_queryset(self):
        return Ordemproducao.objects.using(self.get_banco()).all()

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.save(using=self.get_banco())
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('ordem_producao_web:ordemproducao_list', kwargs={'slug': self.get_slug()})
