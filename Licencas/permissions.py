from rest_framework.permissions import BasePermission

class UsuariosPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        nome = getattr(request.user, "username", None) or getattr(request.user, "usua_nome", None)
        return bool(nome and nome.lower() in ["admin", "mobile", "master"])

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)

