from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import UpdateView

from Entidades.models import Entidades
from Produtos.models import Produtos
from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.forms.abastecimento import AbastecimentoForm
from transportes.models import Abastecusto, Bombas
from transportes.services.servico_de_abastecimento import AbastecimentoService


class AbastecimentosUpdateView(UpdateView):
    model = Abastecusto
    form_class = AbastecimentoForm
    template_name = "transportes/abastecimentos_form.html"

    def _get_banco(self):
        slug = self.kwargs.get("slug")
        return get_db_from_slug(slug) if slug else get_licenca_db_config(self.request)

    def get_success_url(self):
        return reverse("transportes:abastecimentos_lista", kwargs={"slug": self.kwargs["slug"]})

    def get_object(self, queryset=None):
        banco = self._get_banco()
        empresa_id = self.request.session.get("empresa_id")
        filial_id = self.request.session.get("filial_id") or 1
        abas_ctrl = self.kwargs.get("abas_ctrl")
        return get_object_or_404(
            Abastecusto.objects.using(banco),
            abas_empr=empresa_id,
            abas_fili=filial_id,
            abas_ctrl=abas_ctrl,
        )

    def form_valid(self, form):
        banco = self._get_banco()
        usuario_id = self.request.session.get("usua_codi")

        data = form.cleaned_data.copy()
        data["abas_empr"] = self.object.abas_empr
        data["abas_fili"] = self.object.abas_fili

        try:
            self.object = AbastecimentoService.update_abastecimento(
                abastecimento=self.object,
                data=data,
                user_id=usuario_id,
                using=banco,
            )
        except ValueError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        messages.success(self.request, "Abastecimento atualizado com sucesso!")
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["slug"] = self.kwargs.get("slug")
        banco = self._get_banco()
        empresa_id = self.request.session.get("empresa_id")
        obj = self.object

        if obj.abas_frot:
            frota = Entidades.objects.using(banco).filter(enti_empr=empresa_id, enti_clie=obj.abas_frot).first()
            if frota:
                context["frota_display"] = f"{frota.enti_clie} - {frota.enti_nome}"

        if obj.abas_func:
            func = Entidades.objects.using(banco).filter(enti_empr=empresa_id, enti_clie=obj.abas_func).first()
            if func:
                context["funcionario_display"] = f"{func.enti_clie} - {func.enti_nome}"

        if obj.abas_enti:
            forn = Entidades.objects.using(banco).filter(enti_empr=empresa_id, enti_clie=obj.abas_enti).first()
            if forn:
                context["fornecedor_display"] = f"{forn.enti_clie} - {forn.enti_nome}"

        if obj.abas_bomb:
            bomba = Bombas.objects.using(banco).filter(bomb_empr=empresa_id, bomb_codi=obj.abas_bomb).first()
            if bomba:
                context["bomba_display"] = f"{bomba.bomb_codi} - {bomba.bomb_desc}"

        if obj.abas_comb:
            comb = Produtos.objects.using(banco).filter(prod_empr=empresa_id, prod_codi=obj.abas_comb).first()
            if comb:
                context["combustivel_display"] = f"{comb.prod_codi} - {comb.prod_nome}"

        context["titulo"] = "Editar Abastecimento"
        context["acao"] = "Editar"
        return context

