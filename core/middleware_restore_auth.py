from Licencas.models import Usuarios
from core.middleware import get_licenca_slug
from core.utils import get_db_from_slug
import logging

logger = logging.getLogger("licenca.middleware")

class RestoreUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.path.startswith("/web/") or request.path.startswith("/api/"):

            slug = get_licenca_slug() or request.session.get('slug')
            banco = get_db_from_slug(slug) if slug else 'default'

            if request.user.is_authenticated:
                current_db = getattr(request.user, '_state', None).db if hasattr(request.user, '_state') else None
                if current_db == banco:
                    return self.get_response(request)

                username = getattr(request.user, 'usua_nome', None)
                uid = getattr(request.user, 'pk', None)
                usuario_restaurado = None

                if username:
                    try:
                        usuario_restaurado = Usuarios.objects.using(banco).get(usua_nome=username)
                    except Usuarios.DoesNotExist:
                        pass

                if not usuario_restaurado and uid:
                    try:
                        usuario_restaurado = Usuarios.objects.using(banco).get(pk=uid)
                    except Usuarios.DoesNotExist:
                        pass

                if usuario_restaurado:
                    request.user = usuario_restaurado
                    logger.info("[restore_auth] usuario restaurado: %s (DB: %s)",
                                getattr(usuario_restaurado, 'usua_nome', 'Unknown'), banco)

            else:
                uid = request.session.get("usua_codi")
                if uid:
                    try:
                        usuario = Usuarios.objects.using(banco).get(pk=uid)

                        # ✅ Força autenticado SEM chamar django_login() 
                        # (evita rotação do CSRF token)
                        usuario._is_authenticated = True
                        usuario.backend = 'django.contrib.backends.ModelBackend'
                        request.user = usuario

                        logger.info("[restore_auth] usuario recuperado da sessao=%s banco=%s",
                                    getattr(usuario, 'usua_nome', None), banco)

                    except Exception as e:
                        logger.warning("[restore_auth] falha ao restaurar usuario uid=%s err=%s", uid, e)

        return self.get_response(request)