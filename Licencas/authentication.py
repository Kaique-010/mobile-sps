import logging

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.settings import api_settings

from Licencas.models import Usuarios
from core.middleware import get_licenca_slug
from core.utils import get_db_from_slug


logger = logging.getLogger("django")


class CustomJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user_id_claim = getattr(self, "user_id_claim", api_settings.USER_ID_CLAIM)
        user_id_field = getattr(self, "user_id_field", api_settings.USER_ID_FIELD)
        try:
            user_id = validated_token[user_id_claim]
        except KeyError as exc:
            raise InvalidToken("Token inválido: identificador do usuário ausente.") from exc

        slug = (
            validated_token.get("lice_slug")
            or get_licenca_slug()
        )
        banco = get_db_from_slug(slug) if slug else "default"

        usuario = Usuarios.objects.using(banco).filter(**{user_id_field: user_id}).first()

        if usuario is None:
            username = validated_token.get("username") or validated_token.get("usua_nome")
            if username:
                usuario = Usuarios.objects.using(banco).filter(usua_nome__iexact=username).first()

        if usuario is None:
            logger.warning(
                "[jwt_auth] usuário não encontrado user_id=%s slug=%s banco=%s",
                user_id,
                slug,
                banco,
            )
            raise AuthenticationFailed(self.error_messages["user_not_found"], code="user_not_found")

        auth_rule = getattr(self, "user_authentication_rule", None)
        if callable(auth_rule):
            if not auth_rule(usuario):
                raise AuthenticationFailed(self.error_messages["user_inactive"], code="user_inactive")
        else:
            if hasattr(usuario, "is_active") and not usuario.is_active:
                raise AuthenticationFailed(self.error_messages["user_inactive"], code="user_inactive")

        usuario._state.db = banco
        return usuario
