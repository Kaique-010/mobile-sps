from django.views.generic import ListView
from django.contrib import messages
from core.utils import get_db_from_slug
from Produtos.models import Ncm
from CFOP.models import NcmFiscalPadrao
from .web_views import DBAndSlugMixin


class NcmListView(DBAndSlugMixin, ListView):
    model = Ncm
    template_name = "Produtos/list_ncm.html"
    context_object_name = "itens"

    def get_queryset(self):
        db_alias = get_db_from_slug('savexml1') or 'save1'
        qs = Ncm.objects.using(db_alias).all()
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


class NcmFiscalPadraoListView(DBAndSlugMixin, ListView):
    model = NcmFiscalPadrao
    template_name = "Produtos/ncmfiscalpadrao_list.html"
    context_object_name = "itens"

    def get_queryset(self):
        return (
            NcmFiscalPadrao.objects.using(self.db_alias)
            .select_related('ncm')
            .all()
            .order_by('ncm__ncm_codi')
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        return ctx
