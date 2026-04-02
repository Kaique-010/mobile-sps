from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import DeleteView

from ...models import Ordemproducao
from .base import OrdemProducaoWebMixin


class OrdemproducaoDeleteView(OrdemProducaoWebMixin, DeleteView):
    model = Ordemproducao
    template_name = 'OrdemProducao/ordemproducao_confirm_delete.html'
    pk_url_kwarg = 'orpr_codi'

    def get_queryset(self):
        return Ordemproducao.objects.using(self.get_banco()).all()

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete(using=self.get_banco())
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('ordem_producao_web:ordemproducao_list', kwargs={'slug': self.get_slug()})
