from core.utils import get_db_from_slug
from core.middleware import get_licenca_slug  

class LicencaDBRouter:
    def db_for_read(self, model, **hints):
        slug = get_licenca_slug()
        return get_db_from_slug(slug)

    def db_for_write(self, model, **hints):
        slug = get_licenca_slug()
        return get_db_from_slug(slug)
