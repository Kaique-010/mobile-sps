from threading import local
from core.licenca_context import set_licenca_slug
from core.registry import LICENCAS_MAP


_local = local()

def set_licenca_slug(slug):
    _local.licenca_slug = slug

def get_licenca_slug():
    return getattr(_local, 'licenca_slug', None)

class LicencaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path_parts = request.path.strip('/').split('/')

        # Ignorar a verificação de slug na rota de login
        if len(path_parts) >= 3 and path_parts[1] == "licencas" and path_parts[2] == "login":
            return self.get_response(request)

        # Certificar que estamos processando uma URL válida para o slug
        if len(path_parts) < 2 or path_parts[1] == "licencas":
            raise Exception(f"Licença com slug '{path_parts[1]}' não encontrada ou não informada.")
        
        # O slug é o segundo item após /api/{slug}/...
        slug = path_parts[1] if len(path_parts) > 1 else None

        if not slug or not any(lic["slug"] == slug for lic in LICENCAS_MAP):
            raise Exception(f"Licença com slug '{slug}' não encontrada ou não informada.")

        set_licenca_slug(slug)  # Define o slug no contexto
        return self.get_response(request)
