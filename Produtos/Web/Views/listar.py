from django.views.generic import ListView
from django.contrib import messages

from Produtos.models import Ncm
from Produtos.models import NcmAliquota
from ..forms import NcmAliquotaForm
from .web_views import DBAndSlugMixin


class NcmListView(DBAndSlugMixin, ListView):
    model = Ncm
    template_name = "Produtos/list_ncm.html"
    context_object_name = "itens"

    def get_queryset(self):
        qs = Ncm.objects.using(self.db_alias).all()
        q = (self.request.GET.get("q") or "").strip()
        if q:
            from django.db.models import Q
            qs = qs.filter(Q(ncm_codi__icontains=q) | Q(ncm_desc__icontains=q))
        return qs.order_by("ncm_codi")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["busca"] = (self.request.GET.get("q") or "").strip()
        ctx["slug"] = self.slug
        return ctx


class NcmAliquotaListView(DBAndSlugMixin, ListView):
    model = NcmAliquota
    template_name = "Produtos/ncmaliquota_list.html"
    context_object_name = "itens"

    def get_queryset(self):
        return NcmAliquota.objects.using(self.db_alias).select_related('nali_ncm').all().order_by('nali_ncm__ncm_codi')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        return ctx
