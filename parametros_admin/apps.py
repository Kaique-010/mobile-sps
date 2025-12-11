from django.apps import AppConfig
import os
import sys
import logging


class ParametrosAdminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'parametros_admin'
    verbose_name = 'Parâmetros Administrativos'
    
    def ready(self):
        logger = logging.getLogger(__name__)
        try:
            if os.environ.get('DISABLE_PARAM_ADMIN_READY') == '1':
                return
            mgmt_cmds = {'makemigrations', 'migrate', 'collectstatic', 'shell', 'test'}
            if any(cmd in sys.argv for cmd in mgmt_cmds):
                return
            if os.environ.get('RUN_MAIN') != 'true' and 'runserver' in sys.argv:
                return
        except Exception:
            pass
        if getattr(self, '_synced_once', False):
            return
        self._synced_once = True
        try:
            from .models import Modulo
            Modulo.sync_installed_apps(alias='default', force=False)
            logger.info('parametros_admin: módulos sincronizados no alias default')
        except Exception:
            pass
