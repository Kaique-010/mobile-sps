# ordens/permissions.py

from rest_framework.permissions import BasePermission, SAFE_METHODS
from core.registry import get_licenca_db_config


class PodeVerOrdemDoSetor(BasePermission):
    """
    Permission que valida se o usuário pode ver ordens baseado no workflow de setores.
    - Outros setores só veem ordens do seu setor atual ou que podem receber
    """
    
    def has_object_permission(self, request, view, obj):
        setor_user = getattr(request.user, "usua_seto", None) or getattr(request.user, "setor", None)
        
            
        # Usuário sem setor vê tudo
        if not setor_user:
            return True
            
        # Converte setor para int se for string
        try:
            setor_user = int(setor_user)
        except (ValueError, TypeError):
            return False
            
        # Verifica se a ordem está no setor do usuário
        if obj.orde_seto == setor_user:
            return True
            
        # Verifica se o usuário pode receber ordens deste setor (workflow)
        banco = get_licenca_db_config(request)
        if banco:
            from .models import WorkflowSetor
            pode_receber = WorkflowSetor.objects.using(banco).filter(
                wkfl_seto_orig=obj.orde_seto,
                wkfl_seto_dest=setor_user,
                wkfl_ativo=True
            ).exists()
            
            if pode_receber:
                return True
        
        return False

    def has_permission(self, request, view):
        return True


class WorkflowPermission(BasePermission):
    """
    Permission específica para operações de workflow.
    Permite movimentação se:
    1. Usuário sem setor (admin) pode movimentar qualquer ordem
    2. Usuário com setor pode movimentar ordens do seu setor atual
    3. Para avanço, verifica se existe workflow válido do setor atual do usuário
    """
    
    def has_object_permission(self, request, view, obj):
        setor_user = getattr(request.user, "usua_seto", None) or getattr(request.user, "setor", None)
        
        # Usuário sem setor pode movimentar qualquer ordem
        if not setor_user:
            return True
            
        # Converte setor para int se for string
        try:
            setor_user = int(setor_user)
        except (ValueError, TypeError):
            return False
            
        # Verifica se a ordem está no setor do usuário
        if obj.orde_seto == setor_user:
            return True
            
        # Verifica se o usuário pode receber ordens deste setor (workflow)
        banco = get_licenca_db_config(request)
        if banco:
            from .models import WorkflowSetor
            pode_receber = WorkflowSetor.objects.using(banco).filter(
                wkfl_seto_orig=obj.orde_seto,
                wkfl_seto_dest=setor_user,
                wkfl_ativo=True
            ).exists()
            
            if pode_receber:
                return True
        
        return False

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


#Permissão para criar com e editar ordens de serviço com esses usuários apenas 
class OrdemServicoPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        usuario = getattr(request.user, "usua_nome", None)
        if usuario in ["admin", "mobile", "lucas1", "recebimento", "recebimento2", "garantia3"]:
            return True
        return request.method in SAFE_METHODS
    
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
