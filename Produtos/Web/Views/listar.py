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
            .all()
            .order_by('ncm_id')
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        
        # Manual prefetch for NCMs from the correct database
        # Convert queryset to list to evaluate it
        itens = list(ctx['itens'])
        
        if itens:
            ncm_ids = [item.ncm_id for item in itens]
            ncm_db = get_db_from_slug('savexml1') or 'save1'
            # Fetch NCMs
            ncms = Ncm.objects.using(ncm_db).filter(pk__in=ncm_ids)
            ncm_map = {ncm.pk: ncm for ncm in ncms}
            
            for item in itens:
                if item.ncm_id in ncm_map:
                    # Inject the NCM object from the correct DB
                    item.ncm = ncm_map[item.ncm_id]
        
        # Update context with the modified list
        ctx['itens'] = itens
        ctx['object_list'] = itens
        
        return ctx
