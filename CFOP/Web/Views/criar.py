# CFOP/Web/Views/criar.py
from django.urls import reverse
from django.views.generic import CreateView
from django.contrib import messages
from django.shortcuts import redirect
from CFOP.models import CFOP
from ..forms import CFOPForm
from core.utils import get_licenca_db_config  
from Licencas.models import Filiais 


class CFOPCreateView(CreateView):
    model = CFOP
    form_class = CFOPForm
    template_name = "cfop/cfop_form.html"  # seu template

    # --------------------------
    # BANCO / EMPRESA / REGIME
    # --------------------------
    def get_banco(self):
        # seu padrão multi-banco
        return get_licenca_db_config(self.request) or "default"

    def get_empresa(self):
        return self.request.session.get("empresa_id") or self.request.session.get("filial_id", 1)

    def get_filial(self):
        return self.request.session.get("filial_codi") or self.request.GET.get("filial_id")

    def get_regime(self):
        banco = self.get_banco()
        empresa_id = self.get_empresa()
        filial_codi = self.get_filial()
        qs = Filiais.objects.using(banco).filter(empr_codi=empresa_id)
        if filial_codi:
            try:
                qs = qs.filter(empr_codi=int(filial_codi))
            except Exception:
                pass
        filial = qs.first()
        return getattr(filial, "empr_regi_trib", None)

    # --------------------------
    # FORM KWARGS (passa regime)
    # --------------------------
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["regime"] = self.get_regime()
        return kwargs

    # --------------------------
    # INICIAL
    # --------------------------
    def get_initial(self):
        initial = super().get_initial()
        initial["cfop_empr"] = self.get_empresa()
        return initial

    # --------------------------
    # SALVAR
    # --------------------------
    def form_valid(self, form):
        obj = form.save(commit=False)
        # garante empresa
        obj.cfop_empr = self.get_empresa()
        banco = self.get_banco()
        
        try:
            obj.save(using=banco)
            messages.success(self.request, "CFOP criado com sucesso!")
            return redirect(self.get_success_url())
        except ErroDominio as e:
            messages.error(self.request, f"Erro: {e.mensagem}")
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f"Erro ao criar CFOP: {str(e)}")
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["slug"] = self.kwargs.get("slug")
        
        # Agrupamento de campos para manter consistência com o UpdateView
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
            for n in form.fields:
                if n == 'cfop_empr':
                    continue
                
                bf = form[n]
                
                if any(x in n for x in ['icms', 'mva', 'redu', 'difal', 'st']):
                    grouped['icms'].append(bf)
                elif 'ipi' in n:
                    grouped['ipi'].append(bf)
                elif any(x in n for x in ['pis', 'cofins', 'cofi', 'apur']):
                    grouped['pis_cofins'].append(bf)
                elif any(x in n for x in ['ret', 'debi', 'cred', 'iss', 'irr', 'ins']):
                    grouped['retencoes'].append(bf)
                elif 'ibs' in n or 'cbs' in n:
                    grouped['ibs_cbs'].append(bf)
                else:
                    grouped['outros'].append(bf)

        ctx['grouped_fields'] = grouped
        return ctx

    # --------------------------
    # REDIRECIONAMENTO
    # --------------------------
    def get_success_url(self):
        slug = self.kwargs.get("slug")
        return f"/web/{slug}/cfop/"

