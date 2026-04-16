from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView

from Produtos.models import Produtos
from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.forms.bombas_saldos import BombasSaldosForm
from transportes.models import Bombas, BombasSaldos
from transportes.services.bombas_saldos import BombasSaldosService


class BombasSaldosCreateView(CreateView):
    model = BombasSaldos
    form_class = BombasSaldosForm
    template_name = "transportes/bombas_saldos_form.html"

    def _get_banco(self):
        slug = self.kwargs.get("slug")
        return get_db_from_slug(slug) if slug else get_licenca_db_config(self.request)

    def get_success_url(self):
        return reverse("transportes:bombas_saldos_lista", kwargs={"slug": self.kwargs["slug"]})

    def form_valid(self, form):
        banco = self._get_banco()
        empresa_id = self.request.session.get("empresa_id")
        filial_id = self.request.session.get("filial_id") or 1
        usuario_id = self.request.session.get("usua_codi")

        if not empresa_id:
            messages.error(self.request, "Empresa não identificada na sessão.")
            return self.form_invalid(form)

        try:
            self.object, saldo_atual, saldo_depois = BombasSaldosService.registrar_movimentacao(
                using=banco,
                empresa_id=int(empresa_id),
                filial_id=int(filial_id),
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

        messages.success(self.request, f"Movimentação registrada. Saldo: {saldo_atual} → {saldo_depois}")
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["slug"] = self.kwargs.get("slug")
        banco = self._get_banco()
        empresa_id = self.request.session.get("empresa_id")

        bomb_bomb = (self.request.GET.get("bomb_bomb") or "").strip()
        bomb_comb = (self.request.GET.get("bomb_comb") or "").strip()

        if bomb_bomb and empresa_id:
            bomba = Bombas.objects.using(banco).filter(bomb_empr=empresa_id, bomb_codi=bomb_bomb).first()
            if bomba:
                context["bomba_display"] = f"{bomba.bomb_codi} - {bomba.bomb_desc}"
                context["form"].fields["bomb_bomb"].initial = bomb_bomb

        if bomb_comb and empresa_id:
            prod = Produtos.objects.using(banco).filter(prod_empr=str(empresa_id), prod_codi=bomb_comb).first()
            if prod:
                context["combustivel_display"] = f"{prod.prod_codi} - {prod.prod_nome}"
                context["form"].fields["bomb_comb"].initial = bomb_comb

        context["titulo"] = "Nova Movimentação de Combustível"
        context["acao"] = "Criar"
        return context
