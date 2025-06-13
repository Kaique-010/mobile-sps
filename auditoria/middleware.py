from django.utils import timezone
from .models import LogAcao
from core.middleware import get_licenca_slug
from rest_framework.request import Request
from django.forms.models import model_to_dict
from django.apps import apps
from django.utils import timezone
import logging
import json
import re

logger = logging.getLogger(__name__)

class AuditoriaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def extrair_modelo_e_id_da_url(self, url):
        """Extrai o nome do modelo e ID do objeto da URL"""
        # Padrões comuns de URL da API REST
        # /api/licenca/app/modelo/id/ ou /api/licenca/app/modelo/id
        padrao = r'/api/([^/]+)/([^/]+)/([^/]+)/?(?:([0-9]+)/?)?'
        match = re.search(padrao, url)
        
        if match:
            licenca_slug = match.group(1)  # casaa, por exemplo
            app_name = match.group(2)      # entidades
            modelo_name = match.group(3)   # entidades
            objeto_id = match.group(4)     # 77
            
            # Mapear nomes de apps para os nomes reais dos apps Django
            app_mapping = {
                'entidades': 'Entidades',
                'produtos': 'Produtos',
                'pedidos': 'Pedidos',
                'licencas': 'Licencas',
                'caixadiario': 'CaixaDiario',
                'entradas_estoque': 'Entradas_Estoque',
                'saidas_estoque': 'Saidas_Estoque',
                'contas_a_pagar': 'contas_a_pagar',
                'contas_a_receber': 'contas_a_receber',
                'o_s': 'O_S',
                'ordemdeservico': 'OrdemdeServico',
                'orcamentos': 'Orcamentos',
                'listacasamento': 'listacasamento',
                'contratos': 'contratos',
                'dashboards': 'dashboards',
                'auditoria': 'auditoria'
            }
            
            # Usar o nome real do app
            real_app_name = app_mapping.get(app_name.lower(), app_name)
            
            # Tentar obter o modelo real
            try:
                modelo = apps.get_model(real_app_name, modelo_name)
                logger.debug(f'Modelo encontrado: {real_app_name}.{modelo_name}')
                return modelo, objeto_id
            except LookupError:
                logger.debug(f'Modelo não encontrado: {real_app_name}.{modelo_name} (tentativa com {app_name}.{modelo_name})')
                # Tentar com o nome original como fallback
                try:
                    modelo = apps.get_model(app_name, modelo_name)
                    logger.debug(f'Modelo encontrado com fallback: {app_name}.{modelo_name}')
                    return modelo, objeto_id
                except LookupError:
                    logger.debug(f'Modelo não encontrado nem com fallback: {app_name}.{modelo_name}')
                    return None, objeto_id
        
        return None, None
    
    def obter_dados_objeto(self, modelo, objeto_id):
        """Obtém os dados atuais de um objeto antes da alteração"""
        if not modelo or not objeto_id:
            logger.debug(f'Modelo ou ID não fornecido: modelo={modelo}, objeto_id={objeto_id}')
            return None
        
        try:
            logger.debug(f'Tentando obter dados antes para {modelo.__name__} ID {objeto_id}')
            objeto = modelo.objects.get(pk=objeto_id)
            dados = model_to_dict(objeto)
            logger.debug(f'Dados antes capturados com sucesso: {len(dados)} campos')
            return dados
        except (modelo.DoesNotExist, ValueError) as e:
            logger.debug(f'Objeto não encontrado: {modelo.__name__} ID {objeto_id} - Erro: {str(e)}')
            return None
        except Exception as e:
            logger.error(f'Erro inesperado ao obter dados antes: {modelo.__name__} ID {objeto_id} - Erro: {str(e)}')
            return None
    
    def comparar_dados(self, dados_antes, dados_depois):
        """Compara dois dicionários e retorna as diferenças"""
        if not dados_antes or not dados_depois:
            return None
        
        alteracoes = {}
        
        # Verificar campos alterados
        for campo, valor_depois in dados_depois.items():
            valor_antes = dados_antes.get(campo)
            
            # Converter para string para comparação consistente
            str_antes = str(valor_antes) if valor_antes is not None else None
            str_depois = str(valor_depois) if valor_depois is not None else None
            
            if str_antes != str_depois:
                alteracoes[campo] = {
                    'antes': valor_antes,
                    'depois': valor_depois
                }
        
        # Verificar campos removidos
        for campo, valor_antes in dados_antes.items():
            if campo not in dados_depois:
                alteracoes[campo] = {
                    'antes': valor_antes,
                    'depois': None
                }
        
        return alteracoes if alteracoes else None
    
    def processar_dados_resposta(self, response):
        """Extrai dados da resposta para capturar estado posterior"""
        try:
            if hasattr(response, 'data') and response.data:
                return response.data
            elif hasattr(response, 'content'):
                content = response.content.decode('utf-8')
                if content:
                    return json.loads(content)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.debug(f'Erro ao processar dados da resposta: {str(e)}')
        
        return None
    #Vamos chamar o middleware apenas para as rotas da api de todos os apps, em todos os metodos http
    def __call__(self, request):
        if not request.path.startswith('/api/'):
            return self.get_response(request)

        # Ignorar logs para rotas de auditoria (exceto a rota principal)
        if '/auditoria/logs/' in request.path:
            logger.debug(f'Ignorando log para rota de auditoria: {request.path}')
            return self.get_response(request)

        # Capturar dados antes da alteração (para PUT, PATCH, DELETE)
        dados_antes = None
        modelo = None
        objeto_id = None
        
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            logger.debug(f'Método {request.method} detectado, tentando capturar dados antes')
            modelo, objeto_id = self.extrair_modelo_e_id_da_url(request.path)
            logger.debug(f'Modelo extraído: {modelo.__name__ if modelo else None}, ID: {objeto_id}')
            if modelo and objeto_id:
                dados_antes = self.obter_dados_objeto(modelo, objeto_id)
                if dados_antes:
                    logger.debug(f'Dados antes capturados com sucesso para {modelo.__name__} ID {objeto_id}: {list(dados_antes.keys())}')
                else:
                    logger.warning(f'Falha ao capturar dados antes para {modelo.__name__} ID {objeto_id}')
            else:
                logger.debug(f'Modelo ou ID não encontrado na URL: {request.path}')

        # Processar a resposta
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

            # Capturar dados depois da alteração
            dados_depois = None
            campos_alterados = None
            
            if request.method in ['POST', 'PUT', 'PATCH']:
                dados_depois = self.processar_dados_resposta(response)
                
                # Para atualizações, comparar dados antes e depois
                if request.method in ['PUT', 'PATCH'] and dados_antes and dados_depois:
                    campos_alterados = self.comparar_dados(dados_antes, dados_depois)
                    logger.debug(f'Campos alterados detectados: {list(campos_alterados.keys()) if campos_alterados else "Nenhum"}')
            
            # Para DELETE, usar dados_antes como dados_depois (o que foi excluído)
            elif request.method == 'DELETE' and dados_antes:
                dados_depois = dados_antes

            # Extrair informações do modelo se ainda não foram obtidas
            if not modelo or not objeto_id:
                modelo, objeto_id = self.extrair_modelo_e_id_da_url(request.path)
            
            # Extrair o nome da empresa da URL (licença)
            path_parts = request.path.strip('/').split('/')
            empresa = path_parts[1] if len(path_parts) > 1 else None  # casaa, por exemplo

            # Debug dos dados que serão salvos
            logger.debug(f'Dados que serão salvos no log:')
            logger.debug(f'  - dados_antes: {"Sim" if dados_antes else "Não"} ({len(dados_antes) if dados_antes else 0} campos)')
            logger.debug(f'  - dados_depois: {"Sim" if dados_depois else "Não"} ({len(dados_depois) if dados_depois else 0} campos)')
            logger.debug(f'  - campos_alterados: {"Sim" if campos_alterados else "Não"} ({len(campos_alterados) if campos_alterados else 0} campos)')
            
            # Criar o log
            log = LogAcao.objects.create(
                usuario=user,
                data_hora=timezone.now(),
                tipo_acao=method,
                url=url,
                ip=ip,
                navegador=user_agent,
                dados=data,
                dados_antes=dados_antes,
                dados_depois=dados_depois,
                campos_alterados=campos_alterados,
                objeto_id=objeto_id,
                modelo=modelo.__name__ if modelo else None,
                empresa=empresa,
                licenca=licenca_slug
            )

            logger.info(f'Log criado com sucesso: {log.id} - {method} {url}')
            logger.debug(f'Log salvo com dados_antes: {"Sim" if log.dados_antes else "Não"}')

        except Exception as e:
            logger.error(f'Erro ao criar log de auditoria: {str(e)}')
            logger.error(f'URL que causou o erro: {request.path}')
            logger.error(f'Método que causou o erro: {request.method}')
            logger.exception('Detalhes completos do erro:')

        return response