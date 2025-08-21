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
        path_parts = request.path.strip('/').split('/')
        
        if not path_parts or path_parts [0] != 'api':
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

        # Adicionar no método __call__ após linha 34:
        
        # Login simplificado para clientes
        if len(path_parts) >= 3 and path_parts[2] == 'entidades-login-simple':
            slug = path_parts[1]
            request.slug = slug
            set_licenca_slug(slug)
            return self.get_response(request)

        if len(path_parts) < 3 or path_parts[0] != "api":
            raise Exception("URL malformada. Esperado /api/<slug>/...")

        slug = path_parts[1]
      

        licenca = next((lic for lic in LICENCAS_MAP if lic["slug"] == slug), None)
        if not licenca:
            raise Exception(f"Licença com slug '{slug}' não encontrada.")

        # Set no contexto local e request
        set_licenca_slug(slug)
        request.slug = slug
        
        # Sempre usar apenas a API do banco de dados para módulos
        # Não usar fallback para licencas.json
        modulos_disponiveis = []
        try:
            # Importar aqui para evitar circular import
            from parametros_admin.utils import get_modulos_liberados_empresa
            
            # Simular empresa/filial padrão para obter módulos
            empresa_id = 1
            filial_id = 1
            
            # Obter configuração do banco
            banco = get_licenca_db_config(request)

            if banco:
                modulos_db = get_modulos_liberados_empresa(banco, empresa_id, filial_id)
                modulos_disponiveis = modulos_db
             
        except Exception as e:
            print(f"Erro ao obter módulos do banco: {e}")
            print("AVISO: Não foi possível obter módulos do banco. Verifique se a tabela modulosmobile está populada.")
            # Não usar fallback - retornar lista vazia
            modulos_disponiveis = []
        
        set_modulos_disponiveis(modulos_disponiveis)
        request.modulos_disponiveis = modulos_disponiveis

        return self.get_response(request)
