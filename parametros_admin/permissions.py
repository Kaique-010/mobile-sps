from rest_framework.permissions import BasePermission
from core.middleware import get_licenca_slug
from .models import PermissoesModulos, PermissoesRotas
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class PermissaoModuloAvancada(BasePermission):
    """Verifica permissões de módulo com base no banco de dados"""
    
    def has_permission(self, request, view):
        modulo_requerido = getattr(view, 'modulo_necessario', None)
        if not modulo_requerido:
            return True
        
        # Verificar no sistema atual (licencas.json) primeiro
        modulos_disponiveis = getattr(request, 'modulos_disponiveis', [])
        if modulo_requerido not in modulos_disponiveis:
            logger.warning(f"Módulo {modulo_requerido} não disponível na licença")
            return False
        
        # Verificar configuração específica no banco
        return self._check_module_permission(request, modulo_requerido)
    
    def _check_module_permission(self, request, modulo):
        """Verifica permissão específica do módulo no banco"""
        try:
            from core.utils import get_db_from_slug
            banco = get_db_from_slug(get_licenca_slug())
            
            if not banco:
                return True  
            
            cache_key = f"perm_modulo_{banco}_{modulo}"
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
        
            permissao_existe = PermissoesModulos.objects.using(banco).filter(
                perm_modu=modulo,
                perm_ativ=True
            ).exists()
            
            # Se não existe configuração específica, permite (compatibilidade)
            if not permissao_existe:
                result = True
            else:
                # Verificar se não está vencido
                from django.utils import timezone
                permissao = PermissoesModulos.objects.using(banco).filter(
                    perm_modu=modulo,
                    perm_ativ=True
                ).first()
                
                if permissao and permissao.perm_data_venc:
                    result = timezone.now() <= permissao.perm_data_venc
                else:
                    result = True
            
            # Cache por 5 minutos
            cache.set(cache_key, result, 300)
            return result
            
        except Exception as e:
            logger.error(f"Erro ao verificar permissão do módulo {modulo}: {e}")
            return True  # Em caso de erro, permite (fail-safe)

class PermissaoRotaEspecifica(BasePermission):
    """Controle granular por rota e ação"""
    
    def has_permission(self, request, view):
        rota_nome = getattr(view, 'rota_nome', view.__class__.__name__)
        modulo = getattr(view, 'modulo_necessario', 'unknown')
        acao = self._get_acao_from_method(request.method)
        
        return self._check_route_permission(request, modulo, rota_nome, acao)
    
    def _check_route_permission(self, request, modulo, rota_nome, acao):
        """Verifica permissão específica da rota"""
        try:
            from core.utils import get_db_from_slug
            banco = get_db_from_slug(get_licenca_slug())
            
            if not banco:
                return True
            
            # Cache key
            cache_key = f"perm_rota_{banco}_{modulo}_{rota_nome}_{acao}"
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Verificar se existe configuração específica
            permissao_existe = PermissoesRotas.objects.using(banco).filter(
                rota_modu=modulo,
                rota_nome=rota_nome,
                rota_ativ=True
            ).exists()
            
            
            if not permissao_existe:
                result = True
            else:
               
                result = PermissoesRotas.objects.using(banco).filter(
                    rota_modu=modulo,
                    rota_nome=rota_nome,
                    rota_tipo__in=[acao, 'full'],
                    rota_ativ=True
                ).exists()
            
           
            cache.set(cache_key, result, 300)
            return result
            
        except Exception as e:
            logger.error(f"Erro ao verificar permissão da rota {rota_nome}: {e}")
            return True
    
    def _get_acao_from_method(self, method):
        """Mapeia método HTTP para ação"""
        mapping = {
            'GET': 'read',
            'POST': 'create',
            'PUT': 'update',
            'PATCH': 'update',
            'DELETE': 'delete'
        }
        return mapping.get(method, 'read')

class PermissaoAdministrador(BasePermission):
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return (
            getattr(request.user, 'usua_seto', None) == 6 or
            getattr(request.user, 'is_superuser', False) or
            getattr(request.usuarios.usua_nome, 'admin', False)
        )