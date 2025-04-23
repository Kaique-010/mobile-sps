import threading
import json
from django.db import connections
from django.db.utils import ConnectionDoesNotExist
from django.conf import settings
from core.db_config import get_db_config 

_thread_local = threading.local()

def get_current_connection():
    return getattr(_thread_local, "db_connection", None)

class DynamicDatabaseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        docu = request.headers.get('docu')

        if not docu:
            print('[AVISO] Nenhum CNPJ (docu) recebido no header. Usando DB padrão.')
        
        if docu and not settings.USE_LOCAL_DB:
            try:
                db_data = get_db_config(docu)
                db_alias = f'docu_{docu}'

                if db_alias not in connections.databases:
                    connections.databases[db_alias] = {
                        'ENGINE': 'django.db.backends.postgresql',
                        'NAME': db_data["NAME"],
                        'USER': db_data["USER"],
                        'PASSWORD': db_data["PASSWORD"],
                        'HOST': db_data["HOST"],
                        'PORT': db_data["PORT"],
                    }

                _thread_local.db_connection = db_alias
                request.db_alias = db_alias

            except Exception as e:
                print(f"[ERRO] Falha ao configurar banco para docu={docu}: {e}")
                request.db_alias = 'default'
        else:
            request.db_alias = 'default'

        return self.get_response(request)
