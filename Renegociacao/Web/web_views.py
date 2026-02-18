from django.views.generic import ListView, TemplateView
from django.shortcuts import redirect, render
from django.urls import reverse
from decimal import Decimal
from ..models import Renegociado
from ..services.renegociacao_service import RenegociacaoService
from contas_a_receber.Web.mixin import DBAndSlugMixin
from contas_a_receber.models import Titulosreceber


class RenegociacaoListView(DBAndSlugMixin, ListView):
    model = Renegociado
    template_name = "Renegociacao/renegociacao_list.html"
    context_object_name = "renegociacoes"
    paginate_by = 20

    def get_queryset(self):
        qs = Renegociado.objects.using(self.db_alias).all()
        if self.empresa_id:
            qs = qs.filter(rene_empr=self.empresa_id)
        if self.filial_id:
            qs = qs.filter(rene_fili=self.filial_id)
        return qs.order_by("-rene_data", "-rene_id")


class RenegociacaoCreateView(DBAndSlugMixin, TemplateView):
    template_name = "Renegociacao/renegociacao_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        def _to_int(v, default=None):
            try:
                return int(v)
            except (TypeError, ValueError):
                return default
        req = self.request
        emp = req.POST.get("empresa_id") or req.GET.get("empresa_id") or req.session.get("empresa_id") or req.headers.get("X-Empresa") or getattr(req.user, "usua_empr", None) or self.empresa_id or 1
        fil = req.POST.get("filial_id") or req.GET.get("filial_id") or req.session.get("filial_id") or req.headers.get("X-Filial") or getattr(req.user, "usua_fili", None) or self.filial_id or 1
        ctx["empresa_id"] = _to_int(emp, 1)
        ctx["filial_id"] = _to_int(fil, 1)
        return ctx

    def post(self, request, *args, **kwargs):
        def _to_int(v, default=None):
            try:
                return int(v)
            except (TypeError, ValueError):
                return default
        empresa_id = _to_int(
            request.POST.get("empresa_id")
            or request.session.get("empresa_id")
            or request.headers.get("X-Empresa")
            or getattr(request.user, "usua_empr", None)
            or self.empresa_id
            or 1, 1
        )
        filial_id = _to_int(
            request.POST.get("filial_id")
            or request.session.get("filial_id")
            or request.headers.get("X-Filial")
            or getattr(request.user, "usua_fili", None)
            or self.filial_id
            or 1, 1
        )
        usuario_id = int(request.user.id or 0) if hasattr(request, "user") else 0

        titulos_raw = request.POST.get("titulos_ids", "")
        titulos_ids = [t.strip() for t in titulos_raw.split(",") if t.strip()]
        juros = Decimal(request.POST.get("juros", "0") or "0")
        multa = Decimal(request.POST.get("multa", "0") or "0")
        desconto = Decimal(request.POST.get("desconto", "0") or "0")
        parcelas = int(request.POST.get("parcelas", "1") or "1")
        venc_base = request.POST.get("venc_base") or ""
        regra_parc = request.POST.get("regra_parc") or ""
        try:
            RenegociacaoService.criar_renegociacao(
                slug=self.slug,
                empresa_id=empresa_id,
                filial_id=filial_id,
                titulos_ids=titulos_ids,
                juros=juros,
                multa=multa,
                desconto=desconto,
                parcelas=parcelas,
                usuario_id=usuario_id,
                vencimento_base=venc_base,
                regra_parc=regra_parc,
            )
            return redirect(reverse("renegociacao_list", kwargs={"slug": self.slug}))
        except Exception as e:
            ctx = self.get_context_data(**kwargs)
            ctx["erro"] = str(e)
            return render(request, self.template_name, ctx)


class RenegociacaoEditView(DBAndSlugMixin, TemplateView):
    template_name = "Renegociacao/renegociacao_edit.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        rene_id = kwargs.get("rene_id")
        obj = Renegociado.objects.using(self.db_alias).filter(pk=rene_id).first()
        ctx["obj"] = obj
        if obj:
            prefixo_num = f"REN{str(obj.rene_id).zfill(6)}"
            gerados = (Titulosreceber.objects
                                .using(self.db_alias)
                                .filter(titu_titu__startswith=prefixo_num)
                                .values("titu_titu", "titu_seri", "titu_parc", "titu_venc", "titu_valo", "titu_aber")
                                .order_by("titu_venc", "titu_parc"))
            ctx["titulos_gerados"] = list(gerados)
            docs = [d.strip() for d in (obj.rene_titu or "").split(",") if d.strip()]
            if docs:
                originais = (Titulosreceber.objects
                             .using(self.db_alias)
                             .filter(titu_titu__in=docs)
                             .values("titu_titu", "titu_seri", "titu_parc", "titu_venc", "titu_valo", "titu_aber")
                             .order_by("titu_venc", "titu_parc"))
                ctx["titulos_originais"] = list(originais)
        return ctx

    def post(self, request, *args, **kwargs):
        rene_id = int(kwargs.get("rene_id"))
        acao = request.POST.get("acao")
        if acao == "quebrar":
            observ = request.POST.get("observacoes", "")
            usuario_id = int(request.user.id or 0) if hasattr(request, "user") else 0
            try:
                RenegociacaoService.quebrar_acordo(
                    slug=self.slug,
                    renegociacao_id=rene_id,
                    observacoes=observ,
                    usuario_id=usuario_id,
                )
                return redirect(reverse("renegociacao_list", kwargs={"slug": self.slug}))
            except Exception as e:
                ctx = self.get_context_data(**kwargs)
                ctx["erro"] = str(e)
                return render(request, self.template_name, ctx)
        return redirect(reverse("renegociacao_list", kwargs={"slug": self.slug}))
