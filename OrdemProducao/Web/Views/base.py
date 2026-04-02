from core.middleware import get_licenca_slug
from core.utils import get_licenca_db_config


class OrdemProducaoWebMixin:
    template_base = 'OrdemProducao'

    def get_banco(self):
        return get_licenca_db_config(self.request) or 'default'

    def get_slug(self):
        return self.kwargs.get('slug') or get_licenca_slug()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.get_slug()
        return context
