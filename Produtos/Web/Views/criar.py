from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib import messages

from Produtos.models import Ncm
from ..forms import NcmForm
from CFOP.models import NcmFiscalPadrao
from CFOP.Web.forms import NCMFiscalPadraoForm
from .web_views import DBAndSlugMixin
from Licencas.models import Filiais
from CFOP.cst_utils import get_csts_por_regime


class NcmCreateView(DBAndSlugMixin, CreateView):
    model = Ncm
    form_class = NcmForm
    template_name = "Produtos/create_ncm.html"
    def get_success_url(self):
        from django.urls import reverse
        return reverse("ncm_list", kwargs={"slug": self.slug})

    def form_valid(self, form):
        self.object = form.save(commit=False)
        try:
            self.object.save(using=self.db_alias)
        except Exception:
            self.object.save()
        resp = super().form_valid(form)
        messages.success(self.request, "NCM cadastrado com sucesso.")
        return resp

    def form_invalid(self, form):
        if form.errors:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(self.request, f"Erro em {field}: {err}")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["slug"] = self.slug
        return ctx


class NcmFiscalPadraoCreateView(DBAndSlugMixin, CreateView):
    model = NcmFiscalPadrao
    form_class = NCMFiscalPadraoForm    
    template_name = "Produtos/ncmfiscalpadrao_form.html"

    def _get_cst_choices(self):
        try:
            empresa_id = int(self.empresa_id or 1)
            filial_id = int(self.filial_id or 1)
            filial = Filiais.objects.using(self.db_alias).filter(
                empr_empr=empresa_id, 
                empr_codi=filial_id
            ).first()
            regime = filial.empr_regi_trib if filial else '1'
        except Exception:
            regime = '1'
        return get_csts_por_regime(regime)

    def get_success_url(self):
        from django.urls import reverse
        return reverse("ncmfiscalpadrao_list", kwargs={"slug": self.slug})

    def form_valid(self, form):
        self.object = form.save(commit=False)
        try:
            self.object.save(using=self.db_alias)
        except Exception:
            self.object.save()
        messages.success(self.request, "Alíquotas Fiscal Padrão cadastradas com sucesso.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        return ctx

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['cst_choices'] = self._get_cst_choices()
        kwargs['database'] = self.db_alias
        return kwargs


