import threading
from django.http import JsonResponse
import json
import datetime
from django.db import connections
from django.db.utils import ConnectionDoesNotExist
from django.conf import settings
from Auth.models import Licencas
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
            request.db_alias = 'default' 
        else:
            try:

                licenca = Licencas.objects.filter(lice_docu=docu, lice_bloq=False).first()

                if not licenca:
                    print(f"[ERRO] Licença não encontrada ou bloqueada para o CNPJ {docu}")
                    return JsonResponse({"error": "Licença inválida ou bloqueada."}, status=403)

                if licenca._log_data and licenca._log_data < datetime.date.today():
                    print(f"[ERRO] Licença do CNPJ {docu} está expirada.")
                    return JsonResponse({"error": "Licença expirada."}, status=403)

                # Configurando o banco de dados dinâmico
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

            except Licencas.DoesNotExist:
                print(f"[ERRO] CNPJ {docu} não encontrado na tabela de licenças.")
                return JsonResponse({"error": "Licença não encontrada."}, status=404)
            except Exception as e:
                print(f"[ERRO] Falha ao configurar banco para CNPJ {docu}: {e}")
                request.db_alias = 'default'  
        return self.get_response(request)