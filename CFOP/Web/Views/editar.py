from django.views.generic import UpdateView
from django.contrib import messages
from django.shortcuts import redirect
from core.utils import get_licenca_db_config
from ...models import CFOP
from ..forms import CFOPForm

class CFOPUpdateView(UpdateView):
    model = CFOP
    form_class = CFOPForm
    template_name = 'CFOP/cfop_update.html'
    pk_url_kwarg = 'codi'

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug')
        self.db_alias = get_licenca_db_config(request)
        self.empresa_id = (
            kwargs.get('empr')
            or request.session.get('empresa_id')
            or request.headers.get('X-Empresa')
            or request.GET.get('empresa')
        )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = CFOP.objects.using(self.db_alias).all()
        if self.empresa_id:
            qs = qs.filter(cfop_empr=int(self.empresa_id))
        return qs

    def get_object(self, queryset=None):
        empr = int(self.kwargs.get('empr'))
        codi = int(self.kwargs.get('codi'))
        return CFOP.objects.using(self.db_alias).filter(
            cfop_empr=empr, cfop_codi=codi
        ).first()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # se quiser passar REGIME ok, database NÃO
        # kwargs['regime'] = ...
        return kwargs

    def get_success_url(self):
        return f"/web/{self.slug}/cfop/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug

        try:
            qs = CFOP.objects.using(self.db_alias).all()
            if self.empresa_id:
                qs = qs.filter(cfop_empr=int(self.empresa_id))
            ctx['cfops_all'] = qs.order_by('cfop_codi')
        except Exception:
            ctx['cfops_all'] = []

        # ORGANIZAÇÃO DOS GRUPOS
        form = ctx.get('form')
        icms_extra = {
            'cfop_trib_cst_icms', 'cfop_trib_icms', 'cfop_trib_redu',
            'cfop_trib_moda_base', 'cfop_trib_moda_bast', 'cfop_trib_mva',
            'cfop_trib_redu_st', 'cfop_redu_icms_para',
            'cfop_conf_vend_st', 'cfop_perc_dife_aliq',
            'cfop_nao_soma_mva', 'cfop_nao_trib_icms'
        }
        ipi_extra = {
            'cfop_trib_ipi_trib', 'cfop_trib_ipi_nao_trib',
            'cfop_trib_aliq_ipi', 'cfop_nao_trib_ipi'
        }
        piscof_extra = {
            'cfop_trib_cst_pis', 'cfop_trib_perc_pis', 'cfop_trib_valo_pis',
            'cfop_trib_cst_cofins', 'cfop_trib_perc_cofins',
            'cfop_trib_valo_cofins', 'cfop_apur_pis', 'cfop_apur_cofi',
            'cfop_nao_trib_pis'
        }
        ret_extra = {
            'cfop_iss_ret', 'cfop_pis_ret', 'cfop_cof_ret', 'cfop_csl_ret',
            'cfop_irr_ret', 'cfop_ins_ret', 'cfop_bas_ins', 'cfop_bas_irr'
        }

        grouped = {
            'basicos': [],
            'icms': [],
            'ipi': [],
            'pis_cofins': [],
            'retencoes': [],
            'ibs_cbs': [],
            'outros': []
        }

        if form:
            for n in list(form.fields.keys()):
                if n == 'cfop_empr':
                    continue
                bf = form[n]
                if n.startswith('cfop_icms') or n in icms_extra:
                    grouped['icms'].append(bf)
                elif n.startswith('cfop_ipi') or n in ipi_extra:
                    grouped['ipi'].append(bf)
                elif n.startswith('cfop_pis') or n.startswith('cfop_cof') or n in piscof_extra:
                    grouped['pis_cofins'].append(bf)
                elif 'reti' in n or n in ret_extra or 'debi_' in n or 'cred_' in n:
                    grouped['retencoes'].append(bf)
                elif n.startswith('cfop_ibs') or n.startswith('cfop_cbs') or n.startswith('cfop_ibscbs'):
                    grouped['ibs_cbs'].append(bf)
                else:
                    grouped['outros'].append(bf)

        ctx['grouped_fields'] = grouped
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        try:
            obj.save(using=self.db_alias)
            messages.success(self.request, 'CFOP atualizado com sucesso.')
            return redirect(self.get_success_url())
        except Exception as e:
            messages.error(self.request, f'Erro ao atualizar CFOP: {str(e)}')
            return self.form_invalid(form)
