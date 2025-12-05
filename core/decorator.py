from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework import status
from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

def get_modulos_usuario_db(request):
    """Busca módulos liberados do banco de dados para o usuário"""
    try:
        from core.utils import get_licenca_db_config
        from parametros_admin.models import PermissaoModulo
        
        banco = get_licenca_db_config(request)
        if not banco:
            return getattr(request, 'modulos_disponiveis', [])
        
        def _to_int(v, default=None):
            try:
                return int(v)
            except (TypeError, ValueError):
                return default
        # Priorizar cabeçalhos e sessão sobre atributos do usuário
        empresa = _to_int(request.headers.get('X-Empresa')) or request.session.get('empresa_id') or _to_int(getattr(request.user, 'usua_empr', None), 1) or 1
        filial = _to_int(request.headers.get('X-Filial')) or request.session.get('filial_id') or _to_int(getattr(request.user, 'usua_fili', None), 1) or 1
        
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
            parts = (request.path or '').strip('/').split('/')
            is_api = bool(parts and parts[0] == 'api')
            if not is_api:
                try:
                    messages.error(request, f"Módulo '{self.modulo_requerido}' não está liberado para este cliente.")
                except Exception:
                    pass
                try:
                    slug = kwargs.get('slug') or request.session.get('slug')
                    if slug:
                        return redirect(reverse('home_slug', kwargs={'slug': slug}))
                except Exception:
                    pass
                return redirect(reverse('home'))
            raise PermissionDenied(f"Módulo '{self.modulo_requerido}' não está liberado para este cliente.")
        
        return super().dispatch(request, *args, **kwargs)
