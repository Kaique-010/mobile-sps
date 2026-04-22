from django.utils import timezone
from core.utils import get_licenca_db_config


class DBAndSlugMixin:
    slug_url_kwarg = 'slug'

    def dispatch(self, request, *args, **kwargs):
        db_alias = get_licenca_db_config(request)
        setattr(request, 'db_alias', db_alias)

        self.empresa_id = (
            request.session.get('empresa_id')
            or request.headers.get('X-Empresa')
            or request.GET.get('enti_empr')
        )
        self.filial_id = (
            request.session.get('filial_id')
            or request.headers.get('X-Filial')
            or request.GET.get('enti_fili')
        )

        setattr(request, 'empresa_id', self.empresa_id)
        setattr(request, 'filial_id', self.filial_id)

        self.slug = kwargs.get(self.slug_url_kwarg)
        setattr(request, 'slug', self.slug)

        return super().dispatch(request, *args, **kwargs)