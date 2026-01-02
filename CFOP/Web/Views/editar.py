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
        codi = str(self.kwargs.get('codi'))
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
            for n, bf in form.fields.items():
                if n == 'cfop_empr':
                    continue
                
                # Campos básicos (código, descrição, e flags manuais se quiser manter separados ou não)
                # Aqui vamos agrupar conforme padrão de nome
                
                # ICMS / ST / DIFAL
                if any(x in n for x in ['icms', 'mva', 'redu', 'difal', 'st']):
                    grouped['icms'].append(bf)
                
                # IPI
                elif 'ipi' in n:
                    grouped['ipi'].append(bf)
                
                # PIS / COFINS
                elif any(x in n for x in ['pis', 'cofins', 'cofi', 'apur']):
                    grouped['pis_cofins'].append(bf)
                
                # RETENCOES / DEBITO / CREDITO
                elif any(x in n for x in ['ret', 'debi', 'cred', 'iss', 'irr', 'ins']):
                    grouped['retencoes'].append(bf)
                
                # IBS / CBS
                elif 'ibs' in n or 'cbs' in n:
                    grouped['ibs_cbs'].append(bf)
                
                # RESTO
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
