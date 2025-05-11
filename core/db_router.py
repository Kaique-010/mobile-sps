from .registry import get_licenca_db_config

class LicencaDBRouter:
    def db_for_read(self, model, **hints):
        return get_licenca_db_config()

    def db_for_write(self, model, **hints):
        return get_licenca_db_config()