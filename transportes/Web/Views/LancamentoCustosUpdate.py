from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import UpdateView

from Entidades.models import Entidades
from Produtos.models import Produtos
from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.forms.lancamento_custos import LancamentoCustosForm
from transportes.models import Custos, Veiculos
from transportes.services.servico_de_lancamento_custos import LancamentoCustosService


class LancamentoCustosUpdateView(UpdateView):
    model = Custos
    form_class = LancamentoCustosForm
    template_name = "transportes/lancamento_custos_form.html"

    def _get_banco(self):
        slug = self.kwargs.get("slug")
        return get_db_from_slug(slug) if slug else get_licenca_db_config(self.request)

    def get_success_url(self):
        return reverse("transportes:lancamento_custos_lista", kwargs={"slug": self.kwargs["slug"]})

    def get_object(self, queryset=None):
        banco = self._get_banco()
        empresa_id = self.request.session.get("empresa_id")
        filial_id = self.request.session.get("filial_id") or 1
        lacu_ctrl = self.kwargs.get("lacu_ctrl")
        return get_object_or_404(
            Custos.objects.using(banco),
            lacu_empr=empresa_id,
            lacu_fili=filial_id,
            lacu_ctrl=lacu_ctrl,
        )

    def form_valid(self, form):
        banco = self._get_banco()
        usuario_id = self.request.session.get("usua_codi")

        data = form.cleaned_data.copy()
        data["lacu_empr"] = self.object.lacu_empr
        data["lacu_fili"] = self.object.lacu_fili

        try:
            self.object = LancamentoCustosService.update_custo(
                custo=self.object,
                data=data,
                user_id=usuario_id,
                using=banco,
            )
        except ValueError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        messages.success(self.request, "Lançamento de custo atualizado com sucesso!")
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["slug"] = self.kwargs.get("slug")
        banco = self._get_banco()
        empresa_id = self.request.session.get("empresa_id")
        obj = self.object

        if obj.lacu_frot:
            frota = Entidades.objects.using(banco).filter(enti_empr=empresa_id, enti_clie=obj.lacu_frot).first()
            if frota:
                context["frota_display"] = f"{frota.enti_clie} - {frota.enti_nome}"

        if obj.lacu_veic and obj.lacu_frot:
            veic = Veiculos.objects.using(banco).filter(
                veic_empr=empresa_id,
                veic_tran=obj.lacu_frot,
                veic_sequ=obj.lacu_veic,
            ).first()
            if veic:
                context["veiculo_display"] = f"{veic.veic_plac} - {veic.veic_marc or ''} {veic.veic_espe or ''}".strip()

        if obj.lacu_moto:
            func = Entidades.objects.using(banco).filter(enti_empr=empresa_id, enti_clie=obj.lacu_moto).first()
            if func:
                context["funcionario_display"] = f"{func.enti_clie} - {func.enti_nome}"

        if obj.lacu_forn:
            forn = Entidades.objects.using(banco).filter(enti_empr=empresa_id, enti_clie=obj.lacu_forn).first()
            if forn:
                context["fornecedor_display"] = f"{forn.enti_clie} - {forn.enti_nome}"

        if obj.lacu_item:
            prod = Produtos.objects.using(banco).filter(prod_empr=empresa_id, prod_codi=obj.lacu_item).first()
            if prod:
                context["produto_display"] = f"{prod.prod_codi} - {prod.prod_nome}"

        context["titulo"] = "Editar Lançamento de Custo"
        context["acao"] = "Editar"
        return context
