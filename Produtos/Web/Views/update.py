from django.views.generic import UpdateView
from django.urls import reverse_lazy
from django.contrib import messages

from Produtos.models import Ncm
from Produtos.models import NcmAliquota
from ..forms import NcmForm, NcmAliquotaForm
from .web_views import DBAndSlugMixin


class NcmUpdateView(DBAndSlugMixin, UpdateView):
    model = Ncm
    form_class = NcmForm
    template_name = "Produtos/update_ncm.html"
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
        messages.success(self.request, "NCM atualizado com sucesso.")
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

    def get_queryset(self):
        return Ncm.objects.using(self.db_alias).all()


class NcmAliquotaUpdateView(DBAndSlugMixin, UpdateView):
    model = NcmAliquota
    form_class = NcmAliquotaForm
    template_name = "Produtos/ncmaliquota_form.html"
    def get_success_url(self):
        from django.urls import reverse
        return reverse("ncmaliquota_list", kwargs={"slug": self.slug})

    def form_valid(self, form):
        self.object = form.save(commit=False)
        if not self.object.nali_empr:
            try:
                self.object.nali_empr = int(self.empresa_id) if self.empresa_id is not None else 1
            except Exception:
                self.object.nali_empr = 1
        try:
            self.object.save(using=self.db_alias)
        except Exception:
            self.object.save()
        messages.success(self.request, "Alíquotas IBPT atualizadas com sucesso.")
        print("salvar self.object", self.object)
        return super().form_valid(form)

    def get_queryset(self):
        return NcmAliquota.objects.using(self.db_alias).select_related('nali_ncm').all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        return ctx

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['database'] = self.db_alias
        return kwargs
