from rest_framework.permissions import BasePermission
from core.middleware import get_licenca_slug
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
            
            # Buscar módulo pelo nome
            try:
                from .models import Modulo
                modulo_obj = Modulo.objects.get(modu_nome=modulo, modu_ativ=True)
            except Modulo.DoesNotExist:
                # Se não existe no sistema, permite (compatibilidade)
                result = True
            else:
                # Verificar permissão específica
                from .models import PermissaoModulo
                permissao = PermissaoModulo.objects.using(banco).filter(
                    perm_modu=modulo_obj,
                    perm_ativ=True
                ).first()
                
                if not permissao:
                    result = True  # Se não existe configuração específica, permite
                else:
                    # Verificar se não está vencido
                    from django.utils import timezone
                    if permissao.perm_data_venc:
                        result = timezone.now() <= permissao.perm_data_venc
                    else:
                        result = True
            
            # Cache por 5 minutos
            cache.set(cache_key, result, 300)
            return result
            
        except Exception as e:
            logger.error(f"Erro ao verificar permissão do módulo {modulo}: {e}")
            return True  # Em caso de erro, permite (fail-safe)

class PermissaoTelaEspecifica(BasePermission):
    """Controle granular por tela e operação"""
    
    def has_permission(self, request, view):
        tela_codigo = getattr(view, 'tela_codigo', None)
        operacao_codigo = self._get_operacao_from_method(request.method)
        
        if not tela_codigo:
            return True
        
        return self._check_tela_permission(request, tela_codigo, operacao_codigo)
    
    def _check_tela_permission(self, request, tela_codigo, operacao_codigo):
        """Verifica permissão específica da tela"""
        try:
            from core.utils import get_db_from_slug
            banco = get_db_from_slug(get_licenca_slug())
            
            if not banco:
                return True
            
            # Cache key
            cache_key = f"perm_tela_{banco}_{tela_codigo}_{operacao_codigo}"
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Buscar tela e operação
            try:
                from .models import Tela, Operacao
                tela = Tela.objects.get(tela_codigo=tela_codigo, tela_ativ=True)
                operacao = Operacao.objects.get(oper_codigo=operacao_codigo)
            except (Tela.DoesNotExist, Operacao.DoesNotExist):
                result = True  # Se não existe, permite
            else:
                # Verificar permissão específica
                from .models import PermissaoTela
                result = PermissaoTela.objects.using(banco).filter(
                    perm_tela=tela,
                    perm_oper=operacao,
                    perm_ativ=True
                ).exists()
            
            # Cache por 5 minutos
            cache.set(cache_key, result, 300)
            return result
            
        except Exception as e:
            logger.error(f"Erro ao verificar permissão da tela {tela_codigo}: {e}")
            return True
    
    def _get_operacao_from_method(self, method):
        """Mapeia método HTTP para operação"""
        mapping = {
            'GET': 'read',
            'POST': 'create',
            'PUT': 'update',
            'PATCH': 'update',
            'DELETE': 'delete'
        }
        return mapping.get(method, 'read')

class PermissaoAdministrador(BasePermission):
    """Verifica se o usuário é administrador"""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return (
            getattr(request.user, 'usua_seto', None) == 6 or
            getattr(request.user, 'is_superuser', False) or
            getattr(request.user, 'usua_nome', '').lower() == 'admin'
        )

class PermissaoEstoque(BasePermission):
    """Verifica permissões específicas de estoque"""
    
    def has_permission(self, request, view):
        operacao_estoque = getattr(view, 'operacao_estoque', None)
        if not operacao_estoque:
            return True
        
        return self._check_estoque_permission(request, operacao_estoque)
    
    def _check_estoque_permission(self, request, operacao):
        """Verifica permissão de operação de estoque"""
        try:
            from core.utils import get_db_from_slug
            from .models import ParametroSistema, Modulo
            
            banco = get_db_from_slug(get_licenca_slug())
            if not banco:
                return True
            
            empresa = getattr(request.user, 'usua_empr', 1)
            filial = getattr(request.user, 'usua_fili', 1)
            
            # Mapear operações para nomes de parâmetros
            mapeamento_parametros = {
                'pedido_movimenta': 'PEDIDO_MOVIMENTA_ESTOQUE',
                'pedido_volta_estoque': 'PEDIDO_VOLTA_ESTOQUE',
                'orcamento_movimenta': 'ORCAMENTO_MOVIMENTA_ESTOQUE',
                'os_movimenta': 'OS_MOVIMENTA_ESTOQUE',
                'producao_movimenta': 'PRODUCAO_MOVIMENTA_ESTOQUE',
                'estoque_negativo': 'PERMITE_ESTOQUE_NEGATIVO',
                'controle_minimo': 'CONTROLE_ESTOQUE_MINIMO',
                'controle_maximo': 'CONTROLE_ESTOQUE_MAXIMO',
                'alerta_estoque_minimo': 'ALERTA_ESTOQUE_MINIMO',
                'usar_preco_prazo': 'USAR_PRECO_PRAZO',
                'usar_ultimo_preco': 'USAR_ULTIMO_PRECO',
                'desconto_orcamento': 'DESCONTO_ORCAMENTO',
                'desconto_pedido': 'DESCONTO_PEDIDO'
            }
            
            nome_parametro = mapeamento_parametros.get(operacao)
            if not nome_parametro:
                return True
            
            # Buscar o módulo correspondente baseado na operação
            modulo_nome = self._get_modulo_by_operacao(operacao)
            
            try:
                modulo = Modulo.objects.get(modu_nome=modulo_nome, modu_ativ=True)
                
                parametro = ParametroSistema.objects.using(banco).filter(
                    para_empr=empresa,
                    para_fili=filial,
                    para_modu=modulo,
                    para_nome=nome_parametro,
                    para_ativ=True
                ).first()
                
                if parametro:
                    return parametro.para_valo
                else:
                    # Valores padrão se não existe configuração
                    valores_padrao = {
                        'PEDIDO_MOVIMENTA_ESTOQUE': True,
                        'PEDIDO_VOLTA_ESTOQUE': True,
                        'ORCAMENTO_MOVIMENTA_ESTOQUE': False,
                        'OS_MOVIMENTA_ESTOQUE': False,
                        'PRODUCAO_MOVIMENTA_ESTOQUE': False,
                        'PERMITE_ESTOQUE_NEGATIVO': False,
                        'CONTROLE_ESTOQUE_MINIMO': True,
                        'CONTROLE_ESTOQUE_MAXIMO': False,
                        'ALERTA_ESTOQUE_MINIMO': True,
                        'USAR_PRECO_PRAZO': False,
                        'USAR_ULTIMO_PRECO': False,
                        'DESCONTO_ORCAMENTO': True,
                        'DESCONTO_PEDIDO': True
                    }
                    return valores_padrao.get(nome_parametro, True)
                    
            except Modulo.DoesNotExist:
                return True
            
        except Exception as e:
            logger.error(f"Erro ao verificar permissão de estoque {operacao}: {e}")
            return True
    
    def _get_modulo_by_operacao(self, operacao):
        """Retorna o nome do módulo baseado na operação"""
        mapeamento_modulos = {
            'pedido_movimenta': 'Pedidos',
            'pedido_volta_estoque': 'Pedidos',
            'orcamento_movimenta': 'Orcamentos',
            'os_movimenta': 'O_S',
            'producao_movimenta': 'OrdemProducao',
            'estoque_negativo': 'Saidas_Estoque',
            'controle_minimo': 'Entradas_Estoque',
            'controle_maximo': 'Entradas_Estoque',
            'alerta_estoque_minimo': 'Entradas_Estoque',
            'usar_preco_prazo': 'Produtos',
            'usar_ultimo_preco': 'Produtos',
            'desconto_orcamento': 'Orcamentos',
            'desconto_pedido': 'Pedidos'
        }
        return mapeamento_modulos.get(operacao, 'parametros_admin')

class PermissaoFinanceiro(BasePermission):
    """Verifica permissões específicas financeiras"""
    
    def has_permission(self, request, view):
        operacao_financeiro = getattr(view, 'operacao_financeiro', None)
        if not operacao_financeiro:
            return True
        
        return self._check_financeiro_permission(request, operacao_financeiro)
    
    def _check_financeiro_permission(self, request, operacao):
        """Verifica permissão de operação financeira"""
        try:
            from core.utils import get_db_from_slug
            from .models import ConfiguracaoFinanceiro
            
            banco = get_db_from_slug(get_licenca_slug())
            if not banco:
                return True
            
            empresa = getattr(request.user, 'usua_empr', 1)
            filial = getattr(request.user, 'usua_fili', 1)
            
            try:
                config = ConfiguracaoFinanceiro.objects.using(banco).get(
                    conf_empr=empresa,
                    conf_fili=filial
                )
            except ConfiguracaoFinanceiro.DoesNotExist:
                return True  # Se não existe configuração, permite
            
            # Mapear operações para configurações
            mapeamento = {
                'desconto_pedido': config.conf_perm_desc_pedi,
                'acrescimo_pedido': config.conf_perm_acre_pedi,
                'venda_prazo': config.conf_perm_vend_praz,
                'comissao_automatica': config.conf_calc_comi_auto,
                'comissao_desconto': config.conf_comi_sobr_desc
            }
            
            return mapeamento.get(operacao, True)
            
        except Exception as e:
            logger.error(f"Erro ao verificar permissão financeira {operacao}: {e}")
            return True

class PermissaoCombinada(BasePermission):
    """Combina múltiplas permissões"""
    
    def __init__(self, *permission_classes):
        self.permission_classes = permission_classes
    
    def has_permission(self, request, view):
        for permission_class in self.permission_classes:
            permission = permission_class()
            if not permission.has_permission(request, view):
                return False
        return True

# Decoradores para facilitar o uso
def requer_modulo(modulo_nome):
    """Decorador para requerer módulo específico"""
    def decorator(view_class):
        view_class.modulo_necessario = modulo_nome
        return view_class
    return decorator

def requer_tela(tela_codigo):
    """Decorador para requerer tela específica"""
    def decorator(view_class):
        view_class.tela_codigo = tela_codigo
        return view_class
    return decorator

def requer_operacao_estoque(operacao):
    """Decorador para requerer operação de estoque"""
    def decorator(view_class):
        view_class.operacao_estoque = operacao
        return view_class
    return decorator

def requer_operacao_financeiro(operacao):
    """Decorador para requerer operação financeira"""
    def decorator(view_class):
        view_class.operacao_financeiro = operacao
        return view_class
    return decorator