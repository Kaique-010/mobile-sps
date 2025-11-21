from django.views.generic import ListView
from django.core.paginator import Paginator
from core.utils import get_licenca_db_config
from ...models import CFOP

class CFOPListView(ListView):
    model = CFOP    
    template_name = 'CFOP/cfops_list.html'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug')
        self.db_alias = get_licenca_db_config(request)
        self.empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = CFOP.objects.using(self.db_alias).all()
        if self.empresa_id:
            qs = qs.filter(cfop_empr=int(self.empresa_id))
        busca = (self.request.GET.get('q') or '').strip()
        cfop_code = (self.request.GET.get('cfop') or '').strip()
        tipo = (self.request.GET.get('tipo') or '').strip()
        cst_icms = (self.request.GET.get('cst_icms') or '').strip()
        cst_ipi = (self.request.GET.get('cst_ipi') or '').strip()
        cst_pis = (self.request.GET.get('cst_pis') or '').strip()
        cst_cofins = (self.request.GET.get('cst_cofins') or '').strip()
        ini = (self.request.GET.get('ini') or '').strip()
        fim = (self.request.GET.get('fim') or '').strip()
        if busca:
            qs = qs.filter(cfop_desc__icontains=busca)
        if cfop_code:
            try:
                qs = qs.filter(cfop_cfop=int(cfop_code))
            except ValueError:
                pass
        if tipo:
            qs = qs.filter(cfop_tipo__iexact=tipo)
        if cst_icms:
            qs = qs.filter(cfop_trib_cst_icms=cst_icms)
        if cst_ipi:
            qs = qs.filter(cfop_trib_ipi_trib=cst_ipi)
        if cst_pis:
            qs = qs.filter(cfop_trib_cst_pis=cst_pis)
        if cst_cofins:
            qs = qs.filter(cfop_trib_cst_cofins=cst_cofins)
        from django.utils.dateparse import parse_date
        di = parse_date(ini) if ini else None
        df = parse_date(fim) if fim else None
        if di:
            qs = qs.filter(cfop_inic_vali__gte=di)
        if df:
            qs = qs.filter(cfop_fim_vali__lte=df)
        return qs.order_by('cfop_codi')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        ctx['busca'] = (self.request.GET.get('q') or '').strip()
        for k in ['cfop','tipo','cst_icms','cst_ipi','cst_pis','cst_cofins','ini','fim']:
            ctx[k] = (self.request.GET.get(k) or '').strip()
        return ctx