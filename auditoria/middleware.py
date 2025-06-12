from django.utils import timezone
from .models import LogAcao
from core.middleware import get_licenca_slug
from rest_framework.request import Request
import logging

logger = logging.getLogger(__name__)

class AuditoriaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    #Vamos chamar o middleware apenas para as rotas da api de todos os apps, em todos os metodos http
    def __call__(self, request):
        if not request.path.startswith('/api/'):
            return self.get_response(request)

        # Ignorar logs para rotas de auditoria (exceto a rota principal)
        if '/auditoria/logs/' in request.path:
            logger.debug(f'Ignorando log para rota de auditoria: {request.path}')
            return self.get_response(request)

        # Processar a resposta primeiro
        response = self.get_response(request)

        try:
            # Capturar informações após o processamento da ação
            user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
            method = request.method
            url = request.path
            ip = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            # Define a licença como 'auditoria' para endpoints de auditoria
            if request.path.startswith('/api/auditoria/'):
                licenca_slug = 'auditoria'
            else:
                licenca_slug = get_licenca_slug()

            # Log detalhado das informações capturadas
            logger.debug('Informações da requisição:')
            logger.debug(f'URL: {url}')
            logger.debug(f'Método: {method}')
            logger.debug(f'IP: {ip}')
            logger.debug(f'User Agent: {user_agent}')
            logger.debug(f'Usuário: {user}')
            logger.debug(f'Licença: {licenca_slug}')

            # Debug log inicial
            logger.debug(f'Processando log para: {method} {url}')
            logger.debug(f'Usuário autenticado: {user is not None}')
            logger.debug(f'Licença encontrada: {licenca_slug}')

            # Verificações detalhadas de usuário e licença
            # Permitir endpoints públicos sem autenticação
            if request.path.startswith('/api/licencas/mapa/') or '/licencas/login/' in request.path:
                logger.info(f'Endpoint público acessado: {url}')
                return response

            if not user:
                logger.warning(f'Log ignorado - Usuário não autenticado: {url}')
                return response
            
            if not licenca_slug:
                logger.warning(f'Log ignorado - Licença não encontrada: {url} (usuário: {user})')
                return response

            # Tentar obter os dados da requisição
            try:
                if isinstance(request, Request):
                    data = request.data
                else:
                    data = request.body.decode('utf-8') if request.body else None

                if isinstance(data, str):
                    import json
                    data = json.loads(data)
            except Exception as e:
                logger.warning(f'Erro ao processar dados da requisição: {str(e)}')
                data = None

            # Extrair o nome da empresa da URL
            path_parts = request.path.strip('/').split('/')
            empresa = path_parts[1] if len(path_parts) > 1 else None

            # Criar o log
            log = LogAcao.objects.create(
                usuario=user,
                data_hora=timezone.now(),
                tipo_acao=method,
                url=url,
                ip=ip,
                navegador=user_agent,
                dados=data,
                empresa=empresa,
                licenca=licenca_slug
            )

            logger.info(f'Log criado com sucesso: {log.id} - {method} {url}')

        except Exception as e:
            logger.error(f'Erro ao criar log de auditoria: {str(e)}')
            logger.error(f'URL que causou o erro: {request.path}')
            logger.error(f'Método que causou o erro: {request.method}')
            logger.exception('Detalhes completos do erro:')

        return response