from .models import ConfiguracaoEstoque, ConfiguracaoFinanceiro, ParametrosGerais
from core.middleware import get_licenca_slug
from core.utils import get_db_from_slug
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class ParametrosMiddleware:
    """Middleware para carregar parâmetros específicos da empresa"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Carregar configurações
        self._load_configurations(request)
        
        response = self.get_response(request)
        return response
    
    def _load_configurations(self, request):
        """Carrega todas as configurações necessárias"""
        try:
            banco = get_db_from_slug(get_licenca_slug())
            if not banco:
                self._set_default_configs(request)
                return
            
            # Carregar configurações com cache
            self._load_estoque_config(request, banco)
            self._load_financeiro_config(request, banco)
            self._load_parametros_gerais(request, banco)
            
        except Exception as e:
            logger.error(f"Erro ao carregar configurações: {e}")
            self._set_default_configs(request)
    
    def _load_estoque_config(self, request, banco):
        """Carrega configurações de estoque"""
        cache_key = f"estoque_config_{banco}"
        config = cache.get(cache_key)
        
        if config is None:
            try:
                config_obj = ConfiguracaoEstoque.objects.using(banco).first()
                if config_obj:
                    config = {
                        'pedidos_movimentam': config_obj.conf_pedi_move_esto,
                        'orcamentos_movimentam': config_obj.conf_orca_move_esto,
                        'os_movimenta': config_obj.conf_os_move_esto,
                        'producao_movimenta': config_obj.conf_prod_move_esto,
                        'permite_negativo': config_obj.conf_esto_nega,
                        'controla_minimo': config_obj.conf_esto_mini,
                        'controla_maximo': config_obj.conf_esto_maxi,
                        'usa_custo_medio': config_obj.conf_custo_medio,
                        'usa_ultimo_custo': config_obj.conf_custo_ulti
                    }
                else:
                    config = self._get_default_estoque_config()
                
                # Cache por 10 minutos
                cache.set(cache_key, config, 600)
            except Exception as e:
                logger.error(f"Erro ao carregar config estoque: {e}")
                config = self._get_default_estoque_config()
        
        request.estoque_config = config
    
    def _load_financeiro_config(self, request, banco):
        """Carrega configurações financeiras"""
        cache_key = f"financeiro_config_{banco}"
        config = cache.get(cache_key)
        
        if config is None:
            try:
                config_obj = ConfiguracaoFinanceiro.objects.using(banco).first()
                if config_obj:
                    config = {
                        'permite_desconto_pedido': config_obj.conf_perm_desc_pedi,
                        'desconto_maximo_pedido': float(config_obj.conf_desc_maxi_pedi),
                        'permite_acrescimo_pedido': config_obj.conf_perm_acre_pedi,
                        'calcula_comissao_auto': config_obj.conf_calc_comi_auto,
                        'comissao_sobre_desconto': config_obj.conf_comi_sobr_desc,
                        'prazo_maximo_vendas': config_obj.conf_praz_maxi_vend,
                        'permite_vendas_prazo': config_obj.conf_perm_vend_praz
                    }
                else:
                    config = self._get_default_financeiro_config()
                
                cache.set(cache_key, config, 600)
            except Exception as e:
                logger.error(f"Erro ao carregar config financeiro: {e}")
                config = self._get_default_financeiro_config()
        
        request.financeiro_config = config
    
    def _load_parametros_gerais(self, request, banco):
        """Carrega parâmetros gerais"""
        cache_key = f"parametros_gerais_{banco}"
        parametros = cache.get(cache_key)
        
        if parametros is None:
            try:
                parametros_obj = ParametrosGerais.objects.using(banco).filter(
                    para_ativ=True
                ).values('para_nome', 'para_valo', 'para_tipo')
                
                parametros = {}
                for param in parametros_obj:
                    try:
                        if param['para_tipo'] == 'boolean':
                            valor = param['para_valo'].lower() in ['true', '1', 'sim', 'yes']
                        elif param['para_tipo'] == 'integer':
                            valor = int(param['para_valo'])
                        elif param['para_tipo'] == 'decimal':
                            valor = float(param['para_valo'])
                        elif param['para_tipo'] == 'json':
                            import json
                            valor = json.loads(param['para_valo'])
                        else:
                            valor = param['para_valo']
                        
                        parametros[param['para_nome']] = valor
                    except (ValueError, json.JSONDecodeError):
                        parametros[param['para_nome']] = param['para_valo']
                
                cache.set(cache_key, parametros, 600)
            except Exception as e:
                logger.error(f"Erro ao carregar parâmetros gerais: {e}")
                parametros = {}
        
        request.parametros_gerais = parametros
    
    def _get_default_estoque_config(self):
        """Configuração padrão de estoque"""
        return {
            'pedidos_movimentam': True,
            'orcamentos_movimentam': False,
            'os_movimenta': True,
            'producao_movimenta': True,
            'permite_negativo': False,
            'controla_minimo': True,
            'controla_maximo': False,
            'usa_custo_medio': True,
            'usa_ultimo_custo': False
        }
    
    def _get_default_financeiro_config(self):
        """Configuração padrão financeira"""
        return {
            'permite_desconto_pedido': True,
            'desconto_maximo_pedido': 0.0,
            'permite_acrescimo_pedido': True,
            'calcula_comissao_auto': True,
            'comissao_sobre_desconto': False,
            'prazo_maximo_vendas': 0,
            'permite_vendas_prazo': True
        }
    
    def _set_default_configs(self, request):
        """Define configurações padrão"""
        request.estoque_config = self._get_default_estoque_config()
        request.financeiro_config = self._get_default_financeiro_config()
        request.parametros_gerais = {}


class PermissaoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Carregar módulos liberados para a empresa
        if hasattr(request, 'user') and request.user.is_authenticated:
            empresa_id = getattr(request.user, 'usua_empr', 1)
            filial_id = getattr(request.user, 'usua_fili', 1)
            
            modulos_liberados = get_modulos_empresa(request, empresa_id, filial_id)
            request.modulos_liberados = modulos_liberados
            
            # Carregar configurações de estoque e financeiro
            request.estoque_config = get_configuracao_estoque(request, empresa_id, filial_id)
            request.financeiro_config = get_configuracao_financeiro(request, empresa_id, filial_id)
        
        response = self.get_response(request)
        return response