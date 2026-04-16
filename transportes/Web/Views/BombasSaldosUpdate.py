from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import UpdateView

from Produtos.models import Produtos
from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.forms.bombas_saldos import BombasSaldosForm
from transportes.models import Bombas, BombasSaldos
from transportes.services.bombas_saldos import BombasSaldosService


class BombasSaldosUpdateView(UpdateView):
    model = BombasSaldos
    form_class = BombasSaldosForm
    template_name = "transportes/bombas_saldos_form.html"

    def _get_banco(self):
        slug = self.kwargs.get("slug")
        return get_db_from_slug(slug) if slug else get_licenca_db_config(self.request)

    def get_success_url(self):
        return reverse("transportes:bombas_saldos_lista", kwargs={"slug": self.kwargs["slug"]})

    def get_object(self, queryset=None):
        banco = self._get_banco()
        empresa_id = self.request.session.get("empresa_id")
        filial_id = self.request.session.get("filial_id") or 1
        bomb_id = self.kwargs.get("bomb_id")
        return get_object_or_404(
            BombasSaldos.objects.using(banco),
            bomb_id=bomb_id,
            bomb_empr=empresa_id,
            bomb_fili=filial_id,
        )

    def form_valid(self, form):
        banco = self._get_banco()
        empresa_id = self.request.session.get("empresa_id")
        filial_id = self.request.session.get("filial_id") or 1
        usuario_id = self.request.session.get("usua_codi")

        try:
            self.object, saldo_atual, saldo_depois = BombasSaldosService.atualizar_movimentacao(
                using=banco,
                empresa_id=int(empresa_id),
                filial_id=int(filial_id),
                bomb_id=int(self.object.bomb_id),
                bomb_bomb=form.cleaned_data["bomb_bomb"],
                bomb_comb=form.cleaned_data["bomb_comb"],
                tipo_movi=int(form.cleaned_data["bomb_tipo_movi"]),
                quantidade=form.cleaned_data["bomb_sald"],
                data=form.cleaned_data["bomb_data"],
                usuario_id=usuario_id,
            )
        except Exception as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        messages.success(self.request, f"Movimentação atualizada. Saldo: {saldo_atual} → {saldo_depois}")
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["slug"] = self.kwargs.get("slug")
        banco = self._get_banco()
        empresa_id = self.request.session.get("empresa_id")

        if self.object.bomb_bomb:
            bomba = Bombas.objects.using(banco).filter(bomb_empr=empresa_id, bomb_codi=self.object.bomb_bomb).first()
            if bomba:
                context["bomba_display"] = f"{bomba.bomb_codi} - {bomba.bomb_desc}"

        if self.object.bomb_comb:
            prod = Produtos.objects.using(banco).filter(prod_empr=str(empresa_id), prod_codi=self.object.bomb_comb).first()
            if prod:
                context["combustivel_display"] = f"{prod.prod_codi} - {prod.prod_nome}"

        context["titulo"] = "Editar Movimentação de Combustível"
        context["acao"] = "Editar"
        return context

