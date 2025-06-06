from rest_framework.permissions import BasePermission

class PodeVerOrdemDoSetor(BasePermission):
    def has_object_permission(self, request, view, obj):
        setor_user = getattr(request.user, "usua_seto", None)
        return setor_user == 6 or obj.os_seto == setor_user

    def has_permission(self, request, view):
        return True
