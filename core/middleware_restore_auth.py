from django.contrib.auth import login
from Licencas.models import Usuarios

class RestoreUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Só aplicar em rotas web
        if request.path.startswith("/web/"):

            if request.user.is_authenticated:
                return self.get_response(request)

            uid = request.session.get("usua_codi")

            if uid:
                try:
                    usuario = Usuarios.objects.get(pk=uid)
                    login(request, usuario)
                except:
                    pass

        return self.get_response(request)
