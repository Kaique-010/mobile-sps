class GlobalLicencaRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'licencasglobais':
            return 'global'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'licencasglobais':
            return 'global'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Permite relações se ambos forem do mesmo banco
        db_list = ('default', 'global')
        if obj1._state.db in db_list and obj2._state.db in db_list:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'licencasglobais':
            return db == 'global'
        else:
            return db == 'default'
