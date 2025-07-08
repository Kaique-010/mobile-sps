from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from .utils import verificar_permissao_estoque, verificar_permissao_financeiro
from .utils import log_alteracao_detalhada

def requer_permissao_estoque(operacao):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            if not verificar_permissao_estoque(request, operacao):
                return Response(
                    {'error': f'Sem permissão para operação de estoque: {operacao}'},
                    status=status.HTTP_403_FORBIDDEN
                )
            return view_func(self, request, *args, **kwargs)
        return wrapper
    return decorator

def requer_permissao_financeiro(operacao):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            if not verificar_permissao_financeiro(request, operacao):
                return Response(
                    {'error': f'Sem permissão para operação financeira: {operacao}'},
                    status=status.HTTP_403_FORBIDDEN
                )
            return view_func(self, request, *args, **kwargs)
        return wrapper
    return decorator


def log_automatico(tabela):
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            # Capturar dados antes da operação
            if hasattr(self, 'get_object') and request.method in ['PUT', 'PATCH', 'DELETE']:
                try:
                    obj_anterior = self.get_object()
                    dados_anteriores = self.get_serializer(obj_anterior).data
                except:
                    dados_anteriores = None
            else:
                dados_anteriores = None
            
            # Executar operação
            response = func(self, request, *args, **kwargs)
            
            # Log após operação
            if response.status_code < 400:
                acao = {
                    'POST': 'create',
                    'PUT': 'update',
                    'PATCH': 'update',
                    'DELETE': 'delete'
                }.get(request.method, 'read')
                
                registro_id = getattr(response, 'data', {}).get('id') or kwargs.get('pk')
                
                log_alteracao_detalhada(
                    tabela=tabela,
                    registro_id=registro_id,
                    acao=acao,
                    valor_anterior=dados_anteriores,
                    valor_novo=getattr(response, 'data', None),
                    usuario=request.user.usua_nome,
                    ip=request.META.get('REMOTE_ADDR'),
                    detalhes={
                        'endpoint': request.path,
                        'metodo': request.method,
                        'user_agent': request.META.get('HTTP_USER_AGENT')
                    }
                )
            
            return response
        return wrapper
    return decorator