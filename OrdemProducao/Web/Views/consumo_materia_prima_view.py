from django.http import Http404, HttpResponseRedirect
from django.db import connections
from django.urls import reverse
from django.views.generic import FormView

from ...models import MoveEtapaPeso, Ordemproducao
from ...services import OrdemProducaoService
from ..forms import ConsumoMateriaPrimaForm
from .base import OrdemProducaoWebMixin


class ConsumoMateriaPrimaView(OrdemProducaoWebMixin, FormView):
    form_class = ConsumoMateriaPrimaForm
    template_name = "OrdemProducao/consumo_materia_prima_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.banco = self.get_banco()
        try:
            self.ordem = Ordemproducao.objects.using(self.banco).get(pk=int(self.kwargs["orpr_codi"]))
        except Ordemproducao.DoesNotExist:
            raise Http404()
        self.produto_codigo = str(self.kwargs.get("produto_codigo") or "").strip()
        if not self.produto_codigo:
            raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        try:
            table_names = connections[self.banco].introspection.table_names()
            if "moveetapeso" in table_names:
                registro = (
                    MoveEtapaPeso.objects.using(self.banco)
                    .filter(moet_peso_oppr=int(self.ordem.orpr_codi), moet_peso_prod=int(self.produto_codigo))
                    .first()
                )
                if registro:
                    initial["consumido"] = registro.moet_peso_moet or 0
        except Exception:
            pass
        return initial

    def form_valid(self, form):
        usua = int(self.request.session.get("usua_codi") or 0)
        OrdemProducaoService.registrar_consumo_materia_prima(
            ordem=self.ordem,
            using=self.banco,
            produto_codigo=self.produto_codigo,
            consumido=form.cleaned_data["consumido"],
            usua=usua,
        )
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            "ordem_producao_web:ordemproducao_update",
            kwargs={"slug": self.get_slug(), "orpr_codi": int(self.ordem.orpr_codi)},
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["ordem"] = self.ordem
        ctx["produto_codigo"] = self.produto_codigo
        labels = OrdemProducaoService.map_produtos_nomes(using=self.banco, empresa_id=self.ordem.orpr_empr, codigos=[self.produto_codigo])
        ctx["produto_label"] = labels.get(str(self.produto_codigo), str(self.produto_codigo))
        return ctx
