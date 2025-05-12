from .registry import get_licenca_db_config
from core.registry import get_licenca_db_config

class LicencaDBRouter:
    def db_for_read(self, model, **hints):
        slug = get_licenca_db_config()
        if not slug:
            # Evita acesso sem contexto de licença
            return None
        return get_licenca_db_config()

    def db_for_write(self, model, **hints):
        slug = get_licenca_db_config()
        if not slug:
            return None
        return get_licenca_db_config()

    def allow_relation(self, obj1, obj2, **hints):
        # Permite relações apenas entre modelos da mesma base
        db1 = hints.get('database', getattr(obj1._state, 'db', None))
        db2 = hints.get('database', getattr(obj2._state, 'db', None))
        return db1 == db2

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Só aplica migrations no banco default (admin, auth, etc.)
        return db == 'default'
