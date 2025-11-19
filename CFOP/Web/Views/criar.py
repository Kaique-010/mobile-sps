from django.views.generic import CreateView
from django.contrib import messages
from django.shortcuts import redirect
from core.utils import get_licenca_db_config
from ...models import Cfop
from ..forms import CfopForm

class CfopCreateView(CreateView):
    model = Cfop
    form_class = CfopForm
    template_name = 'CFOP/cfop_create.html'

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug')
        self.db_alias = get_licenca_db_config(request)
        self.empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['database'] = self.db_alias
        kwargs['empresa_id'] = self.empresa_id
        return kwargs

    def get_success_url(self):
        return f"/web/{self.slug}/cfop/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        form = ctx.get('form')
        icms_extra = {'cfop_trib_cst_icms','cfop_trib_icms','cfop_trib_redu','cfop_trib_moda_base','cfop_trib_moda_bast','cfop_trib_mva','cfop_trib_redu_st','cfop_redu_icms_para','cfop_conf_vend_st','cfop_perc_dife_aliq','cfop_nao_soma_mva','cfop_nao_trib_icms'}
        ipi_extra = {'cfop_trib_ipi_trib','cfop_trib_ipi_nao_trib','cfop_trib_aliq_ipi','cfop_nao_trib_ipi'}
        piscof_extra = {'cfop_trib_cst_pis','cfop_trib_perc_pis','cfop_trib_valo_pis','cfop_trib_cst_cofins','cfop_trib_perc_cofins','cfop_trib_valo_cofins','cfop_apur_pis','cfop_apur_cofi','cfop_nao_trib_pis'}
        ret_extra = {'cfop_iss_ret','cfop_pis_ret','cfop_cof_ret','cfop_csl_ret','cfop_irr_ret','cfop_ins_ret','cfop_bas_ins','cfop_bas_irr'}
        grouped_fields = {'basicos': [], 'icms': [], 'ipi': [], 'pis_cofins': [], 'retencoes': [], 'ibs_cbs': [], 'outros': []}
        if form:
            for n in list(form.fields.keys()):
                if n == 'cfop_empr':
                    continue
                bf = form[n]
                if n.startswith('cfop_icms') or n in icms_extra:
                    grouped_fields['icms'].append(bf)
                elif n.startswith('cfop_ipi') or n in ipi_extra:
                    grouped_fields['ipi'].append(bf)
                elif n.startswith('cfop_pis') or n.startswith('cfop_cof') or n in piscof_extra:
                    grouped_fields['pis_cofins'].append(bf)
                elif 'reti' in n or n in ret_extra or 'debi_' in n or 'cred_' in n:
                    grouped_fields['retencoes'].append(bf)
                elif n.startswith('cfop_ibs') or n.startswith('cfop_cbs') or n.startswith('cfop_ibscbs'):
                    grouped_fields['ibs_cbs'].append(bf)
                else:
                    grouped_fields['outros'].append(bf)
        ctx['grouped_fields'] = grouped_fields
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        try:
            obj.save(using=self.db_alias)
            messages.success(self.request, 'CFOP criado com sucesso.')
            return redirect(self.get_success_url())
        except Exception as e:
            messages.error(self.request, f'Erro ao salvar CFOP: {str(e)}')
            return self.form_invalid(form)