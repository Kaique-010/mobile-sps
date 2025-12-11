from core.utils import get_db_from_slug
from core.middleware import get_licenca_slug  

class LicencaDBRouter:
    def db_for_read(self, model, **hints):
        slug = get_licenca_slug()
        
        return get_db_from_slug(slug)

    def db_for_write(self, model, **hints):
        slug = get_licenca_slug()
        return get_db_from_slug(slug)
    
    def allow_relation(self, obj1, obj2, **hints):
        """
        Permite relações entre objetos se eles estão no mesmo banco de dados
        """
        db_set = {'default'}
        if obj1._state.db:
            db_set.add(obj1._state.db)
        if obj2._state.db:
            db_set.add(obj2._state.db)
        return True
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Permite migrações em qualquer banco de dados
        """
        return True
