from django.views.generic import UpdateView
from django.contrib import messages
from django.shortcuts import redirect
from core.utils import get_licenca_db_config
from ...models import Os
from ..forms import OsForm
from ...models import PecasOs, ServicosOs
from Entidades.models import Entidades
from Produtos.models import Produtos
from ..formssets import PecasOsFormSet, ServicoOsFormSet

class OsUpdateView(UpdateView):
    model = Os
    form_class = OsForm
    template_name = 'Os/oscriar.html'

    def get_banco(self):
        return get_licenca_db_config(self.request) or 'default'

    def get_empresa(self):
        return self.request.session.get('empresa_id', 1)

    def get_queryset(self):
        return Os.objects.using(self.get_banco()).filter(
            os_empr=self.get_empresa(),
            os_fili=self.request.session.get('filial_id', 1),
        )

    def get_object(self, queryset=None):
        qs = queryset or self.get_queryset()
        return qs.get(os_os=self.kwargs.get('pk'))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['database'] = self.get_banco()
        kwargs['empresa_id'] = self.get_empresa()
        return kwargs

    def get_success_url(self):
        slug = self.kwargs.get('slug')
        return f"/web/{slug}/os/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = self.get_banco()
        empresa = self.get_empresa()
        os_obj = self.object
        if self.request.method == "POST":
            context["pecas_formset"] = PecasOsFormSet(
                self.request.POST,
                prefix="pecas",
                form_kwargs={"database": banco, "empresa_id": empresa},
            )
            context["servicos_formset"] = ServicoOsFormSet(
                self.request.POST,
                prefix="servicos",
                form_kwargs={"database": banco, "empresa_id": empresa},
            )
            return context

        pecas = PecasOs.objects.using(banco).filter(
            peca_empr=os_obj.os_empr,
            peca_fili=os_obj.os_fili,
            peca_os=os_obj.os_os
        ).order_by("peca_item")
        pecas_initial = [
            {
                "peca_prod": p.peca_prod,
                "peca_quan": p.peca_quan,
                "peca_unit": p.peca_unit,
                "peca_desc": p.peca_desc,
                "peca_tota": p.peca_tota,
            }
            for p in pecas
        ]
        servicos = ServicosOs.objects.using(banco).filter(
            serv_empr=os_obj.os_empr,
            serv_fili=os_obj.os_fili,
            serv_os=os_obj.os_os
        ).order_by("serv_item")
        servicos_initial = [
            {
                "serv_prod": s.serv_prod,
                "serv_quan": s.serv_quan,
                "serv_unit": s.serv_unit,
                "serv_desc": s.serv_desc,
                "serv_tota": s.serv_tota,
            }
            for s in servicos
        ]
        produtos_ids = set()
        for p in pecas:
            if p.peca_prod:
                produtos_ids.add(p.peca_prod)
        for s in servicos:
            if s.serv_prod:
                produtos_ids.add(s.serv_prod)
        prod_map = {}
        if produtos_ids:
            produtos = Produtos.objects.using(banco).filter(prod_codi__in=produtos_ids)
            prod_map = {
                prod.prod_codi: f"{prod.prod_codi} - {prod.prod_nome}"
                for prod in produtos
            }
        pecas_display = [
            prod_map.get(item["peca_prod"], item["peca_prod"]) for item in pecas_initial
        ]
        servicos_display = [
            prod_map.get(item["serv_prod"], item["serv_prod"]) for item in servicos_initial
        ]
        for i, item in enumerate(pecas_initial):
            item["display_prod_text"] = pecas_display[i]
        for i, item in enumerate(servicos_initial):
            item["display_prod_text"] = servicos_display[i]
        context["pecas_formset"] = PecasOsFormSet(
            initial=pecas_initial,
            prefix="pecas",
            form_kwargs={"database": banco, "empresa_id": empresa},
        )
        context["servicos_formset"] = ServicoOsFormSet(
            initial=servicos_initial,
            prefix="servicos",
            form_kwargs={"database": banco, "empresa_id": empresa},
        )
        cl = Entidades.objects.using(banco).filter(
            enti_clie=os_obj.os_clie
        ).values("enti_nome").first()
        ve = Entidades.objects.using(banco).filter(
            enti_clie=os_obj.os_resp
        ).values("enti_nome").first()
        context["cliente_display"] = (
            f"{os_obj.os_clie} - {cl['enti_nome']}" if cl else os_obj.os_clie
        )
        context["vendedor_display"] = (
            f"{os_obj.os_resp} - {ve['enti_nome']}" if ve else os_obj.os_resp
        )
        context["slug"] = self.kwargs.get("slug")
        context["is_edit"] = True
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        pecas_fs = context["pecas_formset"]
        serv_fs = context["servicos_formset"]
        banco = self.get_banco()
        if not (form.is_valid() and pecas_fs.is_valid() and serv_fs.is_valid()):
            return self.form_invalid(form)
        try:
            os_obj = self.object
            os_updates = form.cleaned_data.copy()
            os_updates.pop("os_topr", None)
            if hasattr(os_updates.get("os_clie"), "enti_clie"):
                os_updates["os_clie"] = os_updates["os_clie"].enti_clie
            if hasattr(os_updates.get("os_resp"), "enti_clie"):
                os_updates["os_resp"] = os_updates["os_resp"].enti_clie
            pecas_data = []
            for f in pecas_fs:
                if f.cleaned_data and not f.cleaned_data.get("DELETE"):
                    cd = f.cleaned_data
                    prod = cd["peca_prod"]
                    pecas_data.append({
                        "peca_prod": getattr(prod, "prod_codi", prod),
                        "peca_quan": cd["peca_quan"],
                        "peca_unit": cd["peca_unit"],
                        "peca_desc": cd["peca_desc"],
                    })
            serv_data = []
            for f in serv_fs:
                if f.cleaned_data and not f.cleaned_data.get("DELETE"):
                    cd = f.cleaned_data
                    prod = cd["serv_prod"]
                    serv_data.append({
                        "serv_prod": getattr(prod, "prod_codi", prod),
                        "serv_quan": cd["serv_quan"],
                        "serv_unit": cd["serv_unit"],
                        "serv_desc": cd["serv_desc"],
                    })
            if not pecas_data and not serv_data:
                messages.error(self.request, "A OS precisa ter pelo menos uma peça ou serviço.")
                return self.form_invalid(form)
            from ...services.os_service import OsService
            OsService.update_os(
                banco=banco,
                ordem=os_obj,
                os_updates=os_updates,
                pecas_data=pecas_data,
                servicos_data=serv_data,
            )
            messages.success(self.request, f"OS {os_obj.os_os} atualizada com sucesso.")
            return redirect(self.get_success_url())
        except Exception as e:
            messages.error(self.request, f"Erro ao atualizar OS: {e}")
            return self.form_invalid(form)