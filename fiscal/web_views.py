from django.views.generic import TemplateView

from core.middleware import get_licenca_slug


class DevolucoesView(TemplateView):
    template_name = "Fiscal/devolucoes.html"

    def dispatch(self, request, *args, **kwargs):
        slug = (kwargs.get("slug") or get_licenca_slug() or "").strip().lower()
        if slug:
            try:
                request.session["slug"] = slug
            except Exception:
                pass
        return super().dispatch(request, *args, **kwargs)

