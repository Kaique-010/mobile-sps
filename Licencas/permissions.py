from rest_framework.permissions import BasePermission
from django.core import signing
import logging

logger = logging.getLogger(__name__)

USUARIOS_PRIVILEGIADOS = {"admin", "mobile", "master", "web", "lais"}


def get_nome_usuario(request):
    user = getattr(request, "user", None)

    # Campo real do model Usuarios — prioridade máxima
    nome = getattr(user, "usua_nome", None)

    # Fallback: sessão (funciona mesmo antes do user ser populado)
    if not nome:
        try:
            nome = request.session.get("usua_nome")
        except Exception:
            nome = None

    # Fallback: cookie assinado (útil em requests sem sessão ativa)
    if not nome:
        try:
            raw = request.COOKIES.get("mobile_sps_auth_hint")
            if raw:
                payload = signing.loads(raw)
                nome = (payload or {}).get("u")
        except Exception:
            nome = None

    # Fallback: cookie simples (setado pelo frontend) para casos em que o Set-Cookie do login API não propagou
    if not nome:
        try:
            nome = request.COOKIES.get("mobile_sps_user_hint")
        except Exception:
            nome = None

    nome_final = (nome or "").strip().lower()
    logger.debug("[PERM] user=%s usua_nome_resolvido='%s'", user, nome_final)
    return nome_final


def usuario_privilegiado(request) -> bool:
    nome = get_nome_usuario(request)
    return bool(nome and nome in USUARIOS_PRIVILEGIADOS)


class UsuariosPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return usuario_privilegiado(request)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
