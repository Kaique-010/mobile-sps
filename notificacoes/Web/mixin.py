from django.utils import timezone
from core.utils import get_licenca_db_config


class DBAndSlugMixin:
    slug_url_kwarg = 'slug'

    def dispatch(self, request, *args, **kwargs):
        db_alias = get_licenca_db_config(request)
        setattr(request, 'db_alias', db_alias)
        self.db_alias = db_alias

        def _to_int(value, default=None):
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        self.empresa_id = _to_int(
            request.session.get('empresa_id')
            or request.headers.get('X-Empresa')
            or request.GET.get('titu_empr'),
            default=1
        )
        self.filial_id = _to_int(
            request.session.get('filial_id')
            or request.headers.get('X-Filial')
            or request.GET.get('titu_fili'),
            default=1
        )
        self.slug = kwargs.get(self.slug_url_kwarg)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = getattr(self, 'slug', None)
        context['current_year'] = timezone.now().year
        return context

