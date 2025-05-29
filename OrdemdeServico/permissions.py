# ordens/permissions.py

from rest_framework.permissions import BasePermission

class PodeVerOrdemDoSetor(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.orde_seto == request.user.setor

    def has_permission(self, request, view):
        return True 
