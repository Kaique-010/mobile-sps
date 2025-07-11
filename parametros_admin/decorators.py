from functools import wraps
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response
import logging

logger = logging.getLogger(__name__)


def aplicar_parametros_estoque(operacao='entrada'):
    """
    Decorator para aplicar parâmetros de estoque automaticamente
    
    Args:
        operacao: 'entrada', 'saida' ou 'verificacao'
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            try:
                # Obter dados da requisição
                data = request.data if hasattr(request, 'data') else {}
                empresa_id = data.get('empresa_id') or getattr(request.user, 'empresa_id', None)
                filial_id = data.get('filial_id') or getattr(request.user, 'filial_id', None)
                
                if not empresa_id or not filial_id:
                    return Response(
                        {'erro': 'Empresa e filial são obrigatórios'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Importar utils baseado na operação
                from .utils_estoque import (
                    obter_parametros_estoque,
                    verificar_entrada_automatica,
                    verificar_saida_automatica,
                    verificar_estoque_negativo_permitido
                )
                
                # Obter parâmetros de estoque
                parametros = obter_parametros_estoque(empresa_id, filial_id, request)
                
                # Adicionar parâmetros ao contexto da request
                request.parametros_estoque = parametros
                request.empresa_id = empresa_id
                request.filial_id = filial_id
                
                # Verificações específicas por operação
                if operacao == 'entrada':
                    if not verificar_entrada_automatica(empresa_id, filial_id, request):
                        logger.warning(f"Entrada automática desabilitada para empresa {empresa_id}")
                
                elif operacao == 'saida':
                    if not verificar_saida_automatica(empresa_id, filial_id, request):
                        logger.warning(f"Saída automática desabilitada para empresa {empresa_id}")
                    
                    # Verificar se estoque negativo é permitido
                    produto_codigo = data.get('produto_codigo')
                    quantidade = data.get('quantidade', 0)
                    
                    if produto_codigo and quantidade > 0:
                        from .utils_estoque import verificar_estoque_disponivel
                        
                        estoque_ok, estoque_atual = verificar_estoque_disponivel(
                            produto_codigo, quantidade, empresa_id, filial_id, request
                        )
                        
                        if not estoque_ok and not verificar_estoque_negativo_permitido(empresa_id, filial_id, request):
                            return Response(
                                {
                                    'erro': 'Estoque insuficiente',
                                    'estoque_atual': float(estoque_atual),
                                    'quantidade_solicitada': quantidade
                                },
                                status=status.HTTP_400_BAD_REQUEST
                            )
                
                # Executar função original
                response = func(self, request, *args, **kwargs)
                
                # Adicionar informações de parâmetros na resposta se for sucesso
                if hasattr(response, 'data') and isinstance(response.data, dict):
                    response.data['parametros_aplicados'] = {
                        'estoque': {
                            param: info.get('ativo', False) 
                            for param, info in parametros.items()
                        }
                    }
                
                return response
                
            except ValidationError as e:
                return Response(
                    {'erro': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                logger.error(f"Erro no decorator de estoque: {e}")
                return Response(
                    {'erro': 'Erro interno do servidor'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return wrapper
    return decorator


def aplicar_parametros_pedidos(func):
    """
    Decorator para aplicar parâmetros de pedidos automaticamente
    """
    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        try:
            # Obter dados da requisição
            data = request.data if hasattr(request, 'data') else {}
            empresa_id = data.get('empresa_id') or getattr(request.user, 'empresa_id', None)
            filial_id = data.get('filial_id') or getattr(request.user, 'filial_id', None)
            
            if not empresa_id or not filial_id:
                return Response(
                    {'erro': 'Empresa e filial são obrigatórios'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Importar utils de pedidos
            from .utils_pedidos import (
                obter_parametros_pedidos,
                verificar_validacao_estoque,
                obter_preco_produto
            )
            
            # Obter parâmetros de pedidos
            parametros = obter_parametros_pedidos(empresa_id, filial_id, request)
            
            # Adicionar parâmetros ao contexto da request
            request.parametros_pedidos = parametros
            request.empresa_id = empresa_id
            request.filial_id = filial_id
            
            # Verificar validação de estoque se necessário
            if verificar_validacao_estoque(empresa_id, filial_id, request):
                itens = data.get('itens', [])
                for item in itens:
                    produto_codigo = item.get('produto_codigo')
                    quantidade = item.get('quantidade', 0)
                    
                    if produto_codigo and quantidade > 0:
                        from .utils_estoque import verificar_estoque_disponivel
                        
                        estoque_ok, estoque_atual = verificar_estoque_disponivel(
                            produto_codigo, quantidade, empresa_id, filial_id, request
                        )
                        
                        if not estoque_ok:
                            return Response(
                                {
                                    'erro': f'Estoque insuficiente para produto {produto_codigo}',
                                    'estoque_atual': float(estoque_atual),
                                    'quantidade_solicitada': quantidade
                                },
                                status=status.HTTP_400_BAD_REQUEST
                            )
            
            # Executar função original
            response = func(self, request, *args, **kwargs)
            
            # Adicionar informações de parâmetros na resposta se for sucesso
            if hasattr(response, 'data') and isinstance(response.data, dict):
                response.data['parametros_aplicados'] = {
                    'pedidos': {
                        param: info.get('ativo', False) 
                        for param, info in parametros.items()
                    }
                }
            
            return response
            
        except ValidationError as e:
            return Response(
                {'erro': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Erro no decorator de pedidos: {e}")
            return Response(
                {'erro': 'Erro interno do servidor'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return wrapper


def aplicar_parametros_orcamentos(func):
    """
    Decorator para aplicar parâmetros de orçamentos automaticamente
    """
    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        try:
            # Obter dados da requisição
            data = request.data if hasattr(request, 'data') else {}
            empresa_id = data.get('empresa_id') or getattr(request.user, 'empresa_id', None)
            filial_id = data.get('filial_id') or getattr(request.user, 'filial_id', None)
            
            if not empresa_id or not filial_id:
                return Response(
                    {'erro': 'Empresa e filial são obrigatórios'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Importar utils de orçamentos
            from .utils_orcamentos import (
                obter_parametros_orcamentos,
                verificar_baixa_estoque_orcamento,
                calcular_data_validade_orcamento
            )
            
            # Obter parâmetros de orçamentos
            parametros = obter_parametros_orcamentos(empresa_id, filial_id, request)
            
            # Adicionar parâmetros ao contexto da request
            request.parametros_orcamentos = parametros
            request.empresa_id = empresa_id
            request.filial_id = filial_id
            
            # Calcular data de validade se não informada
            if 'data_validade' not in data or not data['data_validade']:
                data['data_validade'] = calcular_data_validade_orcamento(
                    empresa_id, filial_id, request
                )
                request.data = data
            
            # Verificar baixa de estoque se habilitada
            if verificar_baixa_estoque_orcamento(empresa_id, filial_id, request):
                itens = data.get('itens', [])
                for item in itens:
                    produto_codigo = item.get('produto_codigo')
                    quantidade = item.get('quantidade', 0)
                    
                    if produto_codigo and quantidade > 0:
                        from .utils_estoque import verificar_estoque_disponivel
                        
                        estoque_ok, estoque_atual = verificar_estoque_disponivel(
                            produto_codigo, quantidade, empresa_id, filial_id, request
                        )
                        
                        if not estoque_ok:
                            logger.warning(
                                f"Estoque insuficiente para baixa automática em orçamento. "
                                f"Produto: {produto_codigo}, Disponível: {estoque_atual}"
                            )
            
            # Executar função original
            response = func(self, request, *args, **kwargs)
            
            # Adicionar informações de parâmetros na resposta se for sucesso
            if hasattr(response, 'data') and isinstance(response.data, dict):
                response.data['parametros_aplicados'] = {
                    'orcamentos': {
                        param: info.get('ativo', False) 
                        for param, info in parametros.items()
                    }
                }
            
            return response
            
        except ValidationError as e:
            return Response(
                {'erro': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Erro no decorator de orçamentos: {e}")
            return Response(
                {'erro': 'Erro interno do servidor'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return wrapper


def verificar_permissoes_parametros(modulo_nome):
    """
    Decorator para verificar permissões específicas de parâmetros
    
    Args:
        modulo_nome: Nome do módulo ('estoque', 'pedidos', 'orcamentos')
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            try:
                # Verificar se usuário tem permissão para o módulo
                if not hasattr(request.user, 'has_perm'):
                    return Response(
                        {'erro': 'Usuário não autenticado'},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
                
                # Verificar permissões específicas
                permissao_requerida = f'parametros_admin.view_{modulo_nome}_parametros'
                
                if not request.user.has_perm(permissao_requerida):
                    return Response(
                        {'erro': f'Sem permissão para acessar parâmetros de {modulo_nome}'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                # Executar função original
                return func(self, request, *args, **kwargs)
                
            except Exception as e:
                logger.error(f"Erro na verificação de permissões: {e}")
                return Response(
                    {'erro': 'Erro interno do servidor'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return wrapper
    return decorator


def log_operacao_parametros(operacao):
    """
    Decorator para registrar operações com parâmetros
    
    Args:
        operacao: Tipo da operação ('consulta', 'alteracao', 'aplicacao')
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            try:
                # Obter informações da requisição
                usuario = getattr(request.user, 'username', 'anonimo')
                empresa_id = getattr(request, 'empresa_id', None)
                filial_id = getattr(request, 'filial_id', None)
                
                # Log antes da operação
                logger.info(
                    f"Operação de parâmetros iniciada - "
                    f"Usuário: {usuario}, Operação: {operacao}, "
                    f"Empresa: {empresa_id}, Filial: {filial_id}"
                )
                
                # Executar função original
                response = func(self, request, *args, **kwargs)
                
                # Log após a operação
                status_code = getattr(response, 'status_code', 'unknown')
                logger.info(
                    f"Operação de parâmetros concluída - "
                    f"Usuário: {usuario}, Operação: {operacao}, "
                    f"Status: {status_code}"
                )
                
                return response
                
            except Exception as e:
                logger.error(
                    f"Erro na operação de parâmetros - "
                    f"Usuário: {usuario}, Operação: {operacao}, "
                    f"Erro: {str(e)}"
                )
                raise
        
        return wrapper
    return decorator


def validar_dados_obrigatorios(campos_obrigatorios):
    """
    Decorator para validar campos obrigatórios na requisição
    
    Args:
        campos_obrigatorios: Lista de campos obrigatórios
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            try:
                data = request.data if hasattr(request, 'data') else {}
                
                # Verificar campos obrigatórios
                campos_faltando = []
                for campo in campos_obrigatorios:
                    if campo not in data or not data[campo]:
                        campos_faltando.append(campo)
                
                if campos_faltando:
                    return Response(
                        {
                            'erro': 'Campos obrigatórios não informados',
                            'campos_faltando': campos_faltando
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Executar função original
                return func(self, request, *args, **kwargs)
                
            except Exception as e:
                logger.error(f"Erro na validação de dados obrigatórios: {e}")
                return Response(
                    {'erro': 'Erro interno do servidor'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return wrapper
    return decorator


# Decorators combinados para uso comum
def parametros_estoque_completo(operacao='entrada'):
    """
    Decorator combinado para operações de estoque com todas as verificações
    """
    def decorator(func):
        @verificar_permissoes_parametros('estoque')
        @log_operacao_parametros(f'estoque_{operacao}')
        @aplicar_parametros_estoque(operacao)
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


def parametros_pedidos_completo(func):
    """
    Decorator combinado para operações de pedidos com todas as verificações
    """
    @verificar_permissoes_parametros('pedidos')
    @log_operacao_parametros('pedidos')
    @aplicar_parametros_pedidos
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


def parametros_orcamentos_completo(func):
    """
    Decorator combinado para operações de orçamentos com todas as verificações
    """
    @verificar_permissoes_parametros('orcamentos')
    @log_operacao_parametros('orcamentos')
    @aplicar_parametros_orcamentos
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper