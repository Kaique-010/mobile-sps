from django.apps import AppConfig


class ParametrosAdminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'parametros_admin'
    verbose_name = 'Parâmetros Administrativos'
    
    def ready(self):
        try:
            from .models import Modulo
            # Sincroniza no banco padrão
            Modulo.sync_installed_apps(force=True)
            # Sincroniza para todas as licenças conhecidas
            try:
                from core.licenca_context import LICENCAS_MAP
                from core.dbtools import get_db_from_slug
                for lic in LICENCAS_MAP:
                    slug = lic.get('slug')
                    try:
                        alias = get_db_from_slug(slug) or 'default'
                        Modulo.sync_installed_apps(alias=alias, force=True)
                    except Exception:
                        continue
            except Exception:
                pass
        except Exception:
            pass
