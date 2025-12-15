from django.contrib.auth import login
from Licencas.models import Usuarios
from core.middleware import get_licenca_slug
from core.utils import get_db_from_slug
import logging

logger = logging.getLogger("licenca.middleware")

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
                    slug = request.session.get('slug') or get_licenca_slug()
                    banco = get_db_from_slug(slug) if slug else 'default'
                    usuario = Usuarios.objects.using(banco).get(pk=uid)
                    login(request, usuario)
                    try:
                        logger.info("[restore_auth] usuario restaurado=%s banco=%s slug=%s", getattr(usuario, 'usua_nome', None), banco, slug)
                    except Exception:
                        pass
                except Exception as e:
                    try:
                        logger.warning("[restore_auth] falha ao restaurar usuario uid=%s err=%s", uid, e)
                    except Exception:
                        pass

        return self.get_response(request)
