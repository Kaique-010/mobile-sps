from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from core.utils import get_licenca_db_config
from ...models import Cfop
from ..forms import CfopForm

class CfopWizardView(View):
    template_name = 'CFOP/cfop_wizard.html'

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug')
        self.db_alias = get_licenca_db_config(request)
        self.empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
        self.step = request.GET.get('step') or 'basicos'
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = CfopForm(initial={'cfop_empr': self.empresa_id}, database=self.db_alias, empresa_id=self.empresa_id)
        ctx = self._context(form)
        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        form = CfopForm(request.POST, database=self.db_alias, empresa_id=self.empresa_id)
        if request.POST.get('next_step'):
            if form.is_valid():
                return redirect(f"/web/{self.slug}/cfop/wizard/?step={request.POST.get('next_step')}")
            messages.error(request, 'Erros de validação')
        elif request.POST.get('finish'):
            if form.is_valid():
                obj = form.save(commit=False)
                obj.save(using=self.db_alias)
                messages.success(request, 'CFOP salvo')
                return redirect(f"/web/{self.slug}/cfop/")
            messages.error(request, 'Erros de validação')
        ctx = self._context(form)
        return render(request, self.template_name, ctx)

    def _context(self, form):
        grouped_fields = {'basicos': [], 'icms': [], 'ipi': [], 'pis_cofins': [], 'retencoes': [], 'ibs_cbs': [], 'outros': []}
        icms_extra = {'cfop_trib_cst_icms','cfop_trib_icms','cfop_trib_redu','cfop_trib_moda_base','cfop_trib_moda_bast','cfop_trib_mva','cfop_trib_redu_st','cfop_redu_icms_para','cfop_conf_vend_st','cfop_perc_dife_aliq','cfop_nao_soma_mva','cfop_nao_trib_icms'}
        ipi_extra = {'cfop_trib_ipi_trib','cfop_trib_ipi_nao_trib','cfop_trib_aliq_ipi','cfop_nao_trib_ipi'}
        piscof_extra = {'cfop_trib_cst_pis','cfop_trib_perc_pis','cfop_trib_valo_pis','cfop_trib_cst_cofins','cfop_trib_perc_cofins','cfop_trib_valo_cofins','cfop_apur_pis','cfop_apur_cofi','cfop_nao_trib_pis'}
        ret_extra = {'cfop_iss_ret','cfop_pis_ret','cfop_cof_ret','cfop_csl_ret','cfop_irr_ret','cfop_ins_ret','cfop_bas_ins','cfop_bas_irr'}
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
        current_fields = grouped_fields.get(self.step, [])
        return {'form': form, 'grouped_fields': grouped_fields, 'current_fields': current_fields, 'slug': self.slug, 'step': self.step}