from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.views.generic import CreateView, UpdateView

from ...models import Moveetapa, Ordemproducao, Ordemproducaoproduto
from ..forms import MoveetapaForm, OrdemProdutoPrevForm
from .base import OrdemProducaoWebMixin


class OrdemProdutoPrevCreateView(OrdemProducaoWebMixin, CreateView):
    model = Ordemproducaoproduto
    form_class = OrdemProdutoPrevForm
    template_name = "OrdemProducao/ordem_materia_prev_form.html"

    def get_ordem(self):
        banco = self.get_banco()
        ordem = Ordemproducao.objects.using(banco).filter(orpr_codi=self.kwargs.get("orpr_codi")).first()
        if not ordem:
            raise Http404()
        return ordem

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["banco"] = self.get_banco()
        kwargs["empresa_id"] = int(self.request.session.get("empresa_id") or 1)
        return kwargs

    def form_valid(self, form):
        banco = self.get_banco()
        ordem = self.get_ordem()
        self.object = form.save(commit=False)
        self.object.orpr_prod_orpr = ordem
        self.object.orpr_prod_empr = ordem.orpr_empr
        self.object.save(using=banco)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            "ordem_producao_web:ordemproducao_update",
            kwargs={"slug": self.get_slug(), "orpr_codi": self.kwargs.get("orpr_codi")},
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ordem"] = self.get_ordem()
        return context


class MoveetapaCreateView(OrdemProducaoWebMixin, CreateView):
    model = Moveetapa
    form_class = MoveetapaForm
    template_name = "OrdemProducao/ordem_mov_form.html"

    def get_ordem(self):
        banco = self.get_banco()
        ordem = Ordemproducao.objects.using(banco).filter(orpr_codi=self.kwargs.get("orpr_codi")).first()
        if not ordem:
            raise Http404()
        return ordem

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["banco"] = self.get_banco()
        kwargs["empresa_id"] = int(self.request.session.get("empresa_id") or 1)
        return kwargs

    def form_valid(self, form):
        banco = self.get_banco()
        ordem = self.get_ordem()
        self.object = form.save(commit=False)
        self.object.moet_orpr = ordem
        self.object.save(using=banco)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            "ordem_producao_web:ordemproducao_update",
            kwargs={"slug": self.get_slug(), "orpr_codi": self.kwargs.get("orpr_codi")},
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ordem"] = self.get_ordem()
        return context


class MoveetapaUpdateView(OrdemProducaoWebMixin, UpdateView):
    model = Moveetapa
    form_class = MoveetapaForm
    template_name = "OrdemProducao/ordem_mov_form.html"
    pk_url_kwarg = "moet_codi"

    def get_queryset(self):
        return Moveetapa.objects.using(self.get_banco()).all()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["banco"] = self.get_banco()
        kwargs["empresa_id"] = int(self.request.session.get("empresa_id") or 1)
        return kwargs

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.save(using=self.get_banco())
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        ordem = getattr(self.object, "moet_orpr", None)
        if not ordem:
            return reverse("ordem_producao_web:ordemproducao_list", kwargs={"slug": self.get_slug()})
        return reverse("ordem_producao_web:ordemproducao_update", kwargs={"slug": self.get_slug(), "orpr_codi": ordem.orpr_codi})
