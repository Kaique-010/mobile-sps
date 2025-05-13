from rest_framework.response import Response
from rest_framework import status
from functools import wraps

# 🔒 Para travar métodos individuais (actions, custom views etc.)
def modulo_necessario(nome_app):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(self, request, *args, **kwargs):
            modulos = getattr(request, 'modulos_disponiveis', [])
            if nome_app not in modulos:
                return Response(
                    {"erro": f"Módulo '{nome_app}' não está liberado para este cliente."},
                    status=status.HTTP_403_FORBIDDEN
                )
            return view_func(self, request, *args, **kwargs)
        return _wrapped_view
    return decorator

# 🔒 Para travar a ViewSet inteira
class ModuloRequeridoMixin:
    modulo_requerido = None

    def dispatch(self, request, *args, **kwargs):
        modulos = getattr(request, 'modulos_disponiveis', [])
        if self.modulo_requerido and self.modulo_requerido not in modulos:
            return Response(
                {"erro": f"Módulo '{self.modulo_requerido}' não está liberado para este cliente."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().dispatch(request, *args, **kwargs)