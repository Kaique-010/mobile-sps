from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import CreateView, UpdateView

from ...models import Ourives
from ..forms import OurivesForm
from .base import OrdemProducaoWebMixin


class OurivesCreateView(OrdemProducaoWebMixin, CreateView):
    model = Ourives
    form_class = OurivesForm
    template_name = "OrdemProducao/ourives_form.html"

    def get_queryset(self):
        return Ourives.objects.using(self.get_banco()).all()

    def form_valid(self, form):
        banco = self.get_banco()
        empresa_id = int(self.request.session.get("empresa_id") or 1)
        self.object = form.save(commit=False)
        self.object.ouri_empr = empresa_id
        self.object.save(using=banco)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("ordem_producao_web:ordemproducao_list", kwargs={"slug": self.get_slug()})


class OurivesUpdateView(OrdemProducaoWebMixin, UpdateView):
    model = Ourives
    form_class = OurivesForm
    template_name = "OrdemProducao/ourives_form.html"
    pk_url_kwarg = "ouri_codi"

    def get_queryset(self):
        banco = self.get_banco()
        empresa_id = int(self.request.session.get("empresa_id") or 1)
        return Ourives.objects.using(banco).filter(ouri_empr=empresa_id)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.save(using=self.get_banco())
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("ordem_producao_web:ordemproducao_list", kwargs={"slug": self.get_slug()})
