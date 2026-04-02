from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import CreateView, UpdateView

from ...models import Etapa
from ..forms import EtapaForm
from .base import OrdemProducaoWebMixin


class EtapaCreateView(OrdemProducaoWebMixin, CreateView):
    model = Etapa
    form_class = EtapaForm
    template_name = "OrdemProducao/etapa_form.html"

    def get_queryset(self):
        return Etapa.objects.using(self.get_banco()).all()

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.save(using=self.get_banco())
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("ordem_producao_web:ordemproducao_list", kwargs={"slug": self.get_slug()})


class EtapaUpdateView(OrdemProducaoWebMixin, UpdateView):
    model = Etapa
    form_class = EtapaForm
    template_name = "OrdemProducao/etapa_form.html"
    pk_url_kwarg = "etap_codi"

    def get_queryset(self):
        return Etapa.objects.using(self.get_banco()).all()

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.save(using=self.get_banco())
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("ordem_producao_web:ordemproducao_list", kwargs={"slug": self.get_slug()})
