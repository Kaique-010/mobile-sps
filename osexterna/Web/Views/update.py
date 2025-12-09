from django.views.generic import UpdateView
from django.contrib import messages
from django.shortcuts import redirect
from core.utils import get_licenca_db_config
from ...models import Osexterna, Servicososexterna
from ..forms import OsexternaForm, ServicososexternaForm
from Entidades.models import Entidades
from Produtos.models import Produtos
from ..formssets import ServicososexternaFormSet
from ...services.entidade_dados import DadosEntidadesService

class OsUpdateView(UpdateView):
    model = Osexterna
    form_class = OsexternaForm
    template_name = 'Osexterna/criar.html'

    def get_banco(self):
        return get_licenca_db_config(self.request) or 'default'

    def get_empresa(self):
        return self.request.session.get('empresa_id', 1)

    def get_queryset(self):
        return Osexterna.objects.using(self.get_banco()).filter(
            osex_empr=self.get_empresa(),
            osex_fili=self.request.session.get('filial_id', 1),
        )

    def get_object(self, queryset=None):
        qs = queryset or self.get_queryset()
        return qs.get(osex_codi=self.kwargs.get('pk'))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['database'] = self.get_banco()
        kwargs['empresa_id'] = self.get_empresa()
        kwargs['filial_id'] = self.request.session.get('filial_id', 1)
        return kwargs

    def get_success_url(self):
        slug = self.kwargs.get('slug')
        return f"/web/{slug}/osexterna/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = self.get_banco()
        empresa = self.get_empresa()
        os_obj = self.object
        if self.request.method == "POST":
            context["servicos_formset"] = ServicososexternaFormSet(
                data=self.request.POST,
                prefix="servicos",
                form_kwargs={"database": banco, "empresa_id": empresa},
            )
            return context

        servicos = Servicososexterna.objects.using(banco).filter(
            serv_empr=os_obj.osex_empr,
            serv_fili=os_obj.osex_fili,
            serv_os=os_obj.osex_codi
        ).order_by("serv_sequ")
        servicos_initial = [
            {
                "serv_prod": s.serv_prod,
                "serv_quan": s.serv_quan,
                "serv_valo_unit": s.serv_valo_unit,
                "serv_desc": s.serv_desc,
                "serv_valo_tota": s.serv_valo_tota,
            }
            for s in servicos
        ]
        produtos_ids = set(s.serv_prod for s in servicos if getattr(s, 'serv_prod', None))
        prod_map = {}
        if produtos_ids:
            produtos = Produtos.objects.using(banco).filter(prod_codi__in=produtos_ids)
            prod_map = {
                prod.prod_codi: f"{prod.prod_codi} - {prod.prod_nome}"
                for prod in produtos
            }
        servicos_display = [
            prod_map.get(item["serv_prod"], item["serv_prod"]) for item in servicos_initial
        ]
        for i, item in enumerate(servicos_initial):
            item["display_prod_text"] = servicos_display[i]
        context["servicos_formset"] = ServicososexternaFormSet(
            initial=servicos_initial,
            prefix="servicos",
            form_kwargs={"database": banco, "empresa_id": empresa},
        )
        cl = Entidades.objects.using(banco).filter(
            enti_clie=os_obj.osex_clie
        ).values("enti_nome").first()
        ve = Entidades.objects.using(banco).filter(
            enti_clie=os_obj.osex_resp
        ).values("enti_nome").first()
        context["cliente_display"] = (
            f"{os_obj.osex_clie} - {cl['enti_nome']}" if cl else os_obj.osex_clie
        )
        context["vendedor_display"] = (
            f"{os_obj.osex_resp} - {ve['enti_nome']}" if ve else os_obj.osex_resp
        )
        context["slug"] = self.kwargs.get("slug")
        context["is_edit"] = True
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        serv_fs = context["servicos_formset"]
        banco = self.get_banco()
        if not (form.is_valid() and serv_fs.is_valid()):
            return self.form_invalid(form)
        try:
            os_obj = self.object
            os_updates = form.cleaned_data.copy()
            os_updates.pop("os_topr", None)
            if hasattr(os_updates.get("osex_clie"), "enti_clie"):
                os_updates["osex_clie"] = os_updates["osex_clie"].enti_clie
            if hasattr(os_updates.get("osex_resp"), "enti_clie"):
                os_updates["osex_resp"] = os_updates["osex_resp"].enti_clie
            for k, v in os_updates.items():
                setattr(os_obj, k, v)
            serv_data = []
            for f in serv_fs:
                if f.cleaned_data and not f.cleaned_data.get("DELETE"):
                    cd = f.cleaned_data
                    prod = cd["serv_prod"]
                    quan = cd.get("serv_quan", 1) or 1
                    unit = cd.get("serv_valo_unit", 0) or 0
                    total = (float(quan) or 0) * (float(unit) or 0)
                    serv_data.append({
                        "serv_prod": getattr(prod, "prod_codi", prod),
                        "serv_quan": quan,
                        "serv_valo_unit": unit,
                        "serv_valo_tota": total,
                        "serv_desc": cd.get("serv_desc", ""),
                    })
            if not serv_data:
                messages.error(self.request, "A OS precisa ter pelo menos um serviço.")
                return self.form_invalid(form)
            os_obj = DadosEntidadesService.preencher_dados_do_cliente(os_obj, self.request)
            os_obj.save(using=banco)
            # Regravar serviços
            Servicososexterna.objects.using(banco).filter(
                serv_empr=os_obj.osex_empr,
                serv_fili=os_obj.osex_fili,
                serv_os=os_obj.osex_codi,
            ).delete()
            seq = 0
            for item in serv_data:
                seq += 1
                Servicososexterna.objects.using(banco).create(
                    serv_empr=os_obj.osex_empr,
                    serv_fili=os_obj.osex_fili,
                    serv_os=os_obj.osex_codi,
                    serv_sequ=seq,
                    serv_desc=item.get("serv_desc", ""),
                    serv_quan=item.get("serv_quan") or 0,
                    serv_valo_unit=item.get("serv_valo_unit") or 0,
                    serv_valo_tota=item.get("serv_valo_tota") or 0,
                )
            messages.success(self.request, f"OS Externa {os_obj.osex_codi} atualizada com sucesso.")
            return redirect(self.get_success_url())
        except Exception as e:
            messages.error(self.request, f"Erro ao atualizar OS: {e}")
            return self.form_invalid(form)
