from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework import status
from functools import wraps

def get_modulos_usuario_db(request):
    """Busca módulos liberados do banco de dados para o usuário"""
    try:
        from core.utils import get_licenca_db_config
        from parametros_admin.models import PermissaoModulo
        
        banco = get_licenca_db_config(request)
        if not banco:
            return getattr(request, 'modulos_disponiveis', [])
        
        empresa = getattr(request.user, 'usua_empr', 1)
        filial = getattr(request.user, 'usua_fili', 1)
        
        # Buscar módulos liberados no banco
        permissoes = PermissaoModulo.objects.using(banco).filter(
            perm_empr=empresa,
            perm_fili=filial,
            perm_ativ=True
        ).select_related('perm_modu')
        
        modulos_db = [p.perm_modu.modu_nome for p in permissoes if p.perm_modu.modu_ativ]
        
        # Combinar com módulos do JSON (fallback)
        modulos_json = getattr(request, 'modulos_disponiveis', [])
        
        # Retornar união dos módulos (prioridade para o banco)
        return list(set(modulos_db + modulos_json))
        
    except Exception as e:
        # Em caso de erro, usar módulos do JSON
        return getattr(request, 'modulos_disponiveis', [])

# 🔒 Para travar métodos individuais (actions, custom views etc.)
def modulo_necessario(nome_app):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(self, request, *args, **kwargs):
            modulos = get_modulos_usuario_db(request)
            if nome_app not in modulos:
                raise PermissionDenied(f"Módulo '{nome_app}' não está liberado para este cliente.")
            return view_func(self, request, *args, **kwargs)
        return _wrapped_view
    return decorator

# 🔒 Para travar a ViewSet inteira
class ModuloRequeridoMixin:
    modulo_requerido = None

    def dispatch(self, request, *args, **kwargs):
        modulos = get_modulos_usuario_db(request)
        if self.modulo_requerido and self.modulo_requerido not in modulos:
            raise PermissionDenied(f"Módulo '{self.modulo_requerido}' não está liberado para este cliente.")
        return super().dispatch(request, *args, **kwargs)