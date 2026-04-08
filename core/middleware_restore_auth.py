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
                # Usuário já autenticado pelo AuthenticationMiddleware nativo —
                # só corrige o banco se o objeto veio do banco errado (multi-tenancy)
                current_db = getattr(getattr(request.user, '_state', None), 'db', None)

                if current_db != banco:
                    try:
                        usuario = Usuarios.objects.using(banco).get(pk=request.user.pk)
                        request.user = usuario
                        logger.info(
                            "[restore_auth] banco corrigido: %s -> %s usuario=%s",
                            current_db, banco, getattr(usuario, 'usua_nome', None)
                        )
                    except Usuarios.DoesNotExist:
                        logger.warning(
                            "[restore_auth] usuario pk=%s nao encontrado no banco=%s",
                            request.user.pk, banco
                        )
                    except Exception as e:
                        logger.warning("[restore_auth] falha ao trocar banco: %s", e)

            else:
                # AuthenticationMiddleware não reconheceu — fallback pela sessão
                # (cobre casos de sessões antigas sem BACKEND_SESSION_KEY gravado)
                uid = request.session.get("usua_codi")
                if uid:
                    try:
                        usuario = Usuarios.objects.using(banco).get(pk=uid)
                        request.user = usuario
                        logger.info(
                            "[restore_auth] fallback sessao: usuario=%s banco=%s",
                            getattr(usuario, 'usua_nome', None), banco
                        )
                    except Exception as e:
                        logger.warning(
                            "[restore_auth] falha no fallback sessao uid=%s err=%s", uid, e
                        )

        return self.get_response(request)