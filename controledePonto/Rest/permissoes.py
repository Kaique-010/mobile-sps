from rest_framework.permissions import BasePermission
from core.excecoes import ErroDominio

class NaoEAdminNemMobile(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        usuario = getattr(request.user, "usua_nome", None)
        # Permite admin e mobile explicitamente
        if usuario in ["admin", "mobile"]:
            return True
            
        return True
