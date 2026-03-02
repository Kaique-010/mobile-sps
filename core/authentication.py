from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from Licencas.models import Usuarios
from core.middleware import get_licenca_slug
from core.utils import get_db_from_slug
import logging

logger = logging.getLogger("django")

class CustomSessionAuthentication(BaseAuthentication):
    """
    Autenticação customizada que recupera o usuário da sessão Django
    baseada no 'usua_codi' armazenado manualmente pelo login customizado.
    """
    
    def authenticate(self, request):
        # Tenta recuperar o usua_codi da sessão
        usua_codi = request.session.get('usua_codi')
        
        if not usua_codi:
            return None  # Não autenticado via sessão customizada

        # Identifica o banco de dados correto (multi-tenancy)
        slug = get_licenca_slug() or request.session.get('slug')
        banco = get_db_from_slug(slug) if slug else 'default'
        
        try:
            # Tenta buscar o usuário no banco correto
            usuario = Usuarios.objects.using(banco).get(pk=usua_codi)
            # Define o banco de origem no usuário para evitar erros futuros
            usuario._state.db = banco
        except Usuarios.DoesNotExist:
            return None  # Usuário não encontrado, falha na autenticação
        except Exception as e:
            logger.error(f"Erro na autenticação customizada: {e}")
            return None

        # Retorna o usuário autenticado e None (nenhum token associado)
        return (usuario, None)

    def authenticate_header(self, request):
        # Retorna 'Session' para indicar que suporta autenticação via sessão
        return 'Session'
