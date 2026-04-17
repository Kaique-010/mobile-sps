from django.http import Http404
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from core.middleware import get_licenca_slug
from core.utils import get_licenca_db_config


class PrecoMassaTemplateView(TemplateView):
    template_name = "Produtos/preco_massa.html"

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get("slug") or get_licenca_slug()
        self.db_alias = get_licenca_db_config(request)
        if not self.db_alias:
            raise Http404("Banco de dados da licença não encontrado")
        self.empresa_id = (
            request.session.get("empresa_id")
            or request.headers.get("X-Empresa")
            or request.GET.get("empresa")
        )
        self.filial_id = (
            request.session.get("filial_id")
            or request.headers.get("X-Filial")
            or request.GET.get("filial")
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["slug"] = self.slug
        ctx["empresa_id"] = self.empresa_id
        ctx["filial_id"] = self.filial_id
        ctx["api_url"] = reverse_lazy("precos_massa_api_web", kwargs={"slug": self.slug})
        return ctx
