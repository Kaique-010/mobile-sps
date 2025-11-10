import time
from django.core.cache import cache
from django.conf import settings
from threading import local
from core.licenca_context import set_current_request, LICENCAS_MAP
from core.utils import get_licenca_db_config

_local = local()

def set_licenca_slug(slug):
    _local.licenca_slug = slug

def get_licenca_slug():
    return getattr(_local, 'licenca_slug', None)

def set_modulos_disponiveis(modulos):
    _local.modulos_disponiveis = modulos

def get_modulos_disponiveis():
    return getattr(_local, 'modulos_disponiveis', [])

class LicencaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        
        # Rotas que devem ser ignoradas pelo middleware
        ignored_paths = [
            '/api/warm-cache/',
            '/api/licencas/mapa/',
            '/admin/',
            '/static/',
            '/media/',
            '/ws/',
            '/api/schema/', 
            '/api/schema/swagger-ui/',  
        ]
        
        # Verificar se a rota deve ser ignorada
        for ignored_path in ignored_paths:
            if request.path.startswith(ignored_path):
                return self.get_response(request)
        
        path_parts = request.path.strip('/').split('/')
        
        if not path_parts or path_parts[0] != 'api':
            return self.get_response(request)

        # Rotas públicas que não precisam de validação
        if request.path.startswith('/api/licencas/mapa/'):
            return self.get_response(request)
            
        # Nova exceção para login de clientes
        if len(path_parts) >= 3 and path_parts[2] == 'entidades-login':
            # Extrair slug e definir no request sem validação completa
            slug = path_parts[1]
            request.slug = slug
            set_licenca_slug(slug)
            return self.get_response(request)

        # Login simplificado para clientes
        if len(path_parts) >= 3 and path_parts[2] == 'entidades-login-simple':
            slug = path_parts[1]
            request.slug = slug
            set_licenca_slug(slug)
            return self.get_response(request)

        if len(path_parts) < 3 or path_parts[0] != "api":
            raise Exception("URL malformada. Esperado /api/<slug>/...")

        slug = path_parts[1]
        
        # Se slug for 'null' ou 'undefined', tentar extrair do JWT
        if slug in ['null', 'undefined']:
            try:
                import jwt
                
                auth_header = request.headers.get('Authorization', '')
                if auth_header.startswith('Bearer '):
                    token = auth_header.split(' ')[1]
                    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                    jwt_slug = decoded.get('lice_slug')
                    
                    if jwt_slug:
                        slug = jwt_slug
                        path_parts[1] = slug  # Atualizar o path
                    else:
                        from django.http import JsonResponse
                        return JsonResponse(
                            {'error': 'Slug não encontrado no token. Faça login novamente.'},
                            status=401
                        )
                else:
                    from django.http import JsonResponse
                    return JsonResponse(
                        {'error': 'Token de autorização não encontrado.'},
                        status=401
                    )
            except Exception as e:
                from django.http import JsonResponse
                return JsonResponse(
                    {'error': f'Erro ao processar token: {str(e)}'},
                    status=401
                )
        
        licenca_check_start = time.time()
        licenca = next((lic for lic in LICENCAS_MAP if lic["slug"] == slug), None)
        if not licenca:
            raise Exception(f"Licença com slug '{slug}' não encontrada.")
        licenca_check_time = (time.time() - licenca_check_start) * 1000

        # Set no contexto local e request
        set_licenca_slug(slug)
        request.slug = slug
        set_current_request(request)
        
        # Medição do tempo de cache/banco
        cache_start = time.time()
        
        # Cache de módulos por licença (30 minutos - mais tempo)
        # Padrão: ler da sessão se disponível, depois cabeçalho, senão fallback 1
        empresa_id = (
            request.session.get('empresa_id')
            or request.headers.get("X-Empresa")
            or 1
        )
        filial_id = (
            request.session.get('filial_id')
            or request.headers.get("X-Filial")
            or 1
        )
        
        # Log para debug
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"MIDDLEWARE DEBUG - Slug: {slug}, Empresa: {empresa_id}, Filial: {filial_id}")
        logger.info(f"MIDDLEWARE DEBUG - Session empresa_id: {request.session.get('empresa_id')}, filial_id: {request.session.get('filial_id')}")
        logger.info(f"MIDDLEWARE DEBUG - Headers X-Empresa: {request.headers.get('X-Empresa')}, X-Filial: {request.headers.get('X-Filial')}")
        
        cache_key = f"modulos_licenca_{slug}_{empresa_id}_{filial_id}"
        modulos_disponiveis = cache.get(cache_key)
        
        cache_hit = modulos_disponiveis is not None
        
        if modulos_disponiveis is None:
            db_start = time.time()
            try:
                # Importar aqui para evitar circular import
                from parametros_admin.models import PermissaoModulo
                
                # Obter configuração do banco
                banco = get_licenca_db_config(request)

                if banco:
                    # Query otimizada: buscar apenas campos necessários
                    permissoes = PermissaoModulo.objects.using(banco).filter(
                        perm_empr=empresa_id,
                        perm_fili=filial_id,
                        perm_ativ=True,
                        perm_modu__modu_ativ=True  # Filtrar módulos ativos na query
                    ).select_related('perm_modu').only(
                        'perm_modu__modu_nome',  # Apenas o campo necessário
                        'perm_modu__modu_ativ'
                    )
                    
                    # Converter para lista de nomes
                    modulos_disponiveis = [p.perm_modu.modu_nome for p in permissoes]
                    
                    # Cache por 30 minutos (mais tempo)
                    cache.set(cache_key, modulos_disponiveis, 1800)
                else:
                    modulos_disponiveis = []
                     
            except Exception as e:
                print(f"Erro ao obter módulos do banco: {e}")
                print("AVISO: Não foi possível obter módulos do banco. Verifique se a tabela modulosmobile está populada.")
                modulos_disponiveis = []
                # Cache vazio por 5 minutos para evitar queries repetidas em caso de erro
                cache.set(cache_key, modulos_disponiveis, 300)
            
            db_time = (time.time() - db_start) * 1000
        else:
            db_time = 0
            
        cache_total_time = (time.time() - cache_start) * 1000
        
        set_modulos_disponiveis(modulos_disponiveis)
        request.modulos_disponiveis = modulos_disponiveis
        
        middleware_total = (time.time() - start_time) * 1000
        
        # Log detalhado da performance apenas em DEBUG
        if settings.DEBUG:
            print(f"🔍 LICENÇA MIDDLEWARE:")
            print(f"   📋 Licença check: {licenca_check_time:.2f}ms")
            print(f"   💾 Cache {'HIT' if cache_hit else 'MISS'}: {cache_total_time:.2f}ms")
            if not cache_hit:
                print(f"   🗄️  Query DB: {db_time:.2f}ms")
            print(f"   ⏱️  Total middleware: {middleware_total:.2f}ms")
            print(f"   📊 Módulos encontrados: {len(modulos_disponiveis)}")

        return self.get_response(request)

    def process_request(self, request):
        # Priorizar cabeçalhos sobre token JWT
        empresa_id = request.META.get('HTTP_X_EMPRESA')
        filial_id = request.META.get('HTTP_X_FILIAL')
        
        # Se não há cabeçalhos, usar valores do token
        if not empresa_id and hasattr(request, 'user') and hasattr(request.user, 'usua_empr'):
            empresa_id = getattr(request.user, 'usua_empr', 1)
        if not filial_id and hasattr(request, 'user') and hasattr(request.user, 'usua_fili'):
            filial_id = getattr(request.user, 'usua_fili', 1)
        
        # Converter para inteiro
        try:
            empresa_id = int(empresa_id) if empresa_id else 1
            filial_id = int(filial_id) if filial_id else 1
        except (ValueError, TypeError):
            empresa_id = 1
            filial_id = 1
        
        print(f"🔍 [MIDDLEWARE] Empresa: {empresa_id}, Filial: {filial_id}")
        print(f"🔍 [MIDDLEWARE] Headers - X-Empresa: {request.META.get('HTTP_X_EMPRESA')}, X-Filial: {request.META.get('HTTP_X_FILIAL')}")
