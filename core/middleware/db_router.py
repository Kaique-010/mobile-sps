import logging
import os
from django.conf import settings
from django.db import connections
from django.http import JsonResponse
from core.db_config import get_dynamic_db_config, get_license_database
from rest_framework_simplejwt.tokens import AccessToken
from django.utils.deprecation import MiddlewareMixin

# Configuração do logger
logger = logging.getLogger(__name__)

class DynamicDBMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        docu = request.headers.get('X-CNPJ')
        logger.info(f"Recebido CNPJ: {docu}")  # Log para depuração

        if not docu:
            return JsonResponse({'detail': 'CNPJ não enviado no header.'}, status=400)

        try:
            # Aponta para o banco de licenças (SQLite, por exemplo)
            settings.DATABASES['default'] = get_license_database()

            # Busca a configuração do banco para o CNPJ recebido
            db_config = get_dynamic_db_config(docu)

            # Atualiza a configuração do banco com o banco correto
            settings.DATABASES['default'] = db_config

            # Fecha conexões antigas para evitar cache
            for conn in connections.all():
                conn.close()

        except Exception as e:
            logger.error(f'Erro ao configurar o banco de dados: {str(e)}')  # Log de erro
            return JsonResponse({'detail': f'Erro ao configurar o banco de dados: {str(e)}'}, status=500)

        return self.get_response(request)


class JWTDBMiddleware(MiddlewareMixin):
    def process_request(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION')
        if auth and auth.startswith('Bearer '):
            token = auth.split(' ')[1]
            try:
                # Valida o token JWT
                access = AccessToken(token)
                db_name = access.get('db_name')
                logger.info(f"Banco extraído do token JWT: {db_name}")  # Log para depuração

                if db_name:
                    # Define o caminho para o banco de dados
                    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dbs', f'{db_name}.sqlite3')

                    # Valida se o banco de dados existe
                    if not os.path.exists(db_path):
                        logger.error(f"Banco de dados {db_name} não encontrado no caminho {db_path}")
                        return JsonResponse({'detail': 'Banco de dados não encontrado'}, status=500)

                    # Atualiza a configuração do banco de dados com o caminho correto
                    settings.DATABASES['default'] = {
                        'ENGINE': 'django.db.backends.sqlite3',
                        'NAME': db_path,
                    }

                    # Fecha as conexões antigas para evitar cache de conexão
                    for conn in connections.all():
                        conn.close()

            except Exception as e:
                logger.error(f"Erro ao processar o token JWT: {str(e)}")  # Log de erro
                # Caso não haja erro crítico, a requisição continua
                pass
