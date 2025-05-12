from threading import local
from core.licenca_context import set_current_request, LICENCAS_MAP

_local = local()

def set_licenca_slug(slug):
    _local.licenca_slug = slug

def get_licenca_slug():
    return getattr(_local, 'licenca_slug', None)

class LicencaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Extrai as partes da URL
        path_parts = request.path.strip('/').split('/')
        print(f"URL dividida em partes: {path_parts}")
        
        # Se a requisição for para o mapa de licenças, não precisa de slug
        if request.path.startswith('/api/licencas/mapa/'):
            return self.get_response(request)

        # O slug deve estar sempre na URL após '/api/'
        if len(path_parts) < 3 or path_parts[0] != "api":
            raise Exception("URL malformada. Esperado /api/<slug>/licencas/...")

        # Extrai o slug
        slug = path_parts[1]
        print(f"Slug extraído: {slug}")

        # Verifica se o slug é válido
        if not any(lic["slug"] == slug for lic in LICENCAS_MAP):
            raise Exception(f"Licença com slug '{slug}' não encontrada ou não informada.")

        # Definir o banco de dados da licença
        set_licenca_slug(slug)

        return self.get_response(request)