# CFOP/Web/Views/criar.py
from django.urls import reverse
from django.views.generic import CreateView
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
        obj = form.instance
        # garante empresa
        obj.cfop_empr = self.get_empresa()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["slug"] = self.kwargs.get("slug")
        return ctx

    # --------------------------
    # REDIRECIONAMENTO
    # --------------------------
    def get_success_url(self):
        slug = self.kwargs.get("slug")
        return f"/web/{slug}/cfop/"
        # ou reverse("cfop_list", kwargs={"slug": slug})
