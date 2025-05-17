from threading import local
from core.licenca_context import set_current_request, LICENCAS_MAP

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
        print(f"URL dividida em partes: {path_parts}")
        
        if not path_parts or path_parts [0] != 'api':
            return self.get_response(request)

        if request.path.startswith('/api/licencas/mapa/'):
            return self.get_response(request)

        if len(path_parts) < 3 or path_parts[0] != "api":
            raise Exception("URL malformada. Esperado /api/<slug>/...")

        slug = path_parts[1]
        print(f"Slug extraído: {slug}")

        licenca = next((lic for lic in LICENCAS_MAP if lic["slug"] == slug), None)
        if not licenca:
            raise Exception(f"Licença com slug '{slug}' não encontrada.")

        # Set no contexto local e request
        set_licenca_slug(slug)
        set_modulos_disponiveis(licenca.get("modulos", []))

        # Joga direto no request também
        request.slug = slug
        request.modulos_disponiveis = licenca.get("modulos", [])

        return self.get_response(request)
