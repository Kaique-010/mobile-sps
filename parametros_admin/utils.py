from django.core.cache import cache
from pprint import pprint
from django.utils import timezone
from parametros_admin.models import Modulo, PermissaoModulo
from core.registry import get_licenca_db_config
import logging
import json

logger = logging.getLogger(__name__)

def log_alteracao(tabela, registro_id, acao, valor_anterior, valor_novo, usuario, ip=None):
    """Registra alteração nos logs"""
    try:
        from .models import LogParametros
        LogParametros.objects.create(
            log_tabe=tabela,
            log_regi=registro_id,
            log_acao=acao,
            log_valo_ante=json.dumps(valor_anterior) if valor_anterior else '',
            log_valo_novo=json.dumps(valor_novo) if valor_novo else '',
            log_usua=usuario,
            log_ip=ip
        )
    except Exception as e:
        logger.error(f"Erro ao registrar log: {e}")

def get_parametro(request, nome_parametro, default=None):
    """Obtém valor de um parâmetro específico"""
    parametros = getattr(request, 'parametros_gerais', {})
    return parametros.get(nome_parametro, default)





def verificar_permissao_tela(request, tela_codigo, operacao_codigo):
    """Verifica se uma operação em uma tela está liberada"""
    try:
        banco = get_licenca_db_config(request)
        if not banco:
            return True
        
        empresa = getattr(request.user, 'usua_empr', 1)
        filial = getattr(request.user, 'usua_fili', 1)
        
        # Cache key
        cache_key = f"perm_tela_{banco}_{empresa}_{filial}_{tela_codigo}_{operacao_codigo}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        try:
            from .models import Tela, Operacao, PermissaoTela
            tela = Tela.objects.get(tela_codigo=tela_codigo, tela_ativ=True)
            operacao = Operacao.objects.get(oper_codigo=operacao_codigo)
        except (Tela.DoesNotExist, Operacao.DoesNotExist):
            result = True  # Se não existe, permite
        else:
            result = PermissaoTela.objects.using(banco).filter(
                perm_empr=empresa,
                perm_fili=filial,
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

def verificar_permissao_estoque(request, operacao):
    """Verifica se uma operação de estoque é permitida"""
    try:
        from .models import ConfiguracaoEstoque
        
        banco = get_licenca_db_config(request)
        if not banco:
            return True
        
        empresa = getattr(request.user, 'usua_empr', 1)
        filial = getattr(request.user, 'usua_fili', 1)
        
        try:
            config = ConfiguracaoEstoque.objects.using(banco).get(
                conf_empr=empresa,
                conf_fili=filial
            )
        except ConfiguracaoEstoque.DoesNotExist:
            return True  # Se não existe configuração, permite
        
        # Mapear operações para configurações
        mapeamento = {
            'pedido_movimenta': config.conf_pedi_move_esto,
            'orcamento_movimenta': config.conf_orca_move_esto,
            'os_movimenta': config.conf_os_move_esto,
            'producao_movimenta': config.conf_prod_move_esto,
            'estoque_negativo': config.conf_esto_nega,
            'controle_minimo': config.conf_esto_mini,
            'controle_maximo': config.conf_esto_maxi
        }
        
        return mapeamento.get(operacao, True)
        
    except Exception as e:
        logger.error(f"Erro ao verificar permissão de estoque {operacao}: {e}")
        return True

def verificar_permissao_financeiro(request, operacao):
    """Verifica se uma operação financeira é permitida"""
    try:
        from .models import ConfiguracaoFinanceiro
        
        banco = get_licenca_db_config(request)
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

def get_desconto_maximo(request):
    """Retorna o desconto máximo permitido"""
    try:
        from .models import ConfiguracaoFinanceiro
        
        banco = get_licenca_db_config(request)
        if not banco:
            return 0.0
        
        empresa = getattr(request.user, 'usua_empr', 1)
        filial = getattr(request.user, 'usua_fili', 1)
        
        try:
            config = ConfiguracaoFinanceiro.objects.using(banco).get(
                conf_empr=empresa,
                conf_fili=filial
            )
            return float(config.conf_desc_maxi_pedi)
        except ConfiguracaoFinanceiro.DoesNotExist:
            return 0.0
        
    except Exception as e:
        logger.error(f"Erro ao obter desconto máximo: {e}")
        return 0.0

def limpar_cache_configuracoes(banco=None):
    """Limpa cache de configurações"""
    if banco:
        cache.delete(f"estoque_config_{banco}")
        cache.delete(f"financeiro_config_{banco}")
        cache.delete(f"parametros_gerais_{banco}")
    else:
        # Limpar todos os caches relacionados
        cache.delete_many([
            key for key in cache._cache.keys() 
            if any(prefix in key for prefix in ['estoque_config_', 'financeiro_config_', 'parametros_gerais_', 'perm_modulo_', 'perm_tela_'])
        ])

def get_modulos_usuario(request):
    """Retorna módulos liberados para o usuário"""
    try:
        banco = get_licenca_db_config(request)
        if not banco:
            return []
        
        empresa = getattr(request.user, 'usua_empr', 1)
        filial = getattr(request.user, 'usua_fili', 1)
        
        # Cache key
        cache_key = f"modulos_usuario_{banco}_{empresa}_{filial}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        from .models import PermissaoModulo
        modulos_liberados = PermissaoModulo.objects.using(banco).filter(
            perm_empr=empresa,
            perm_fili=filial,
            perm_ativ=True
        ).select_related('perm_modu')
        
        # Filtrar módulos vencidos
        modulos_ativos = []
        for permissao in modulos_liberados:
            if not permissao.perm_data_venc or timezone.now() <= permissao.perm_data_venc:
                modulos_ativos.append(permissao.perm_modu.modu_nome)
        
        # Cache por 5 minutos
        cache.set(cache_key, modulos_ativos, 300)
        return modulos_ativos
        
    except Exception as e:
        logger.error(f"Erro ao obter módulos do usuário: {e}")
        return []

def get_telas_usuario(request):
    """Retorna telas e operações liberadas para o usuário"""
    try:
        banco = get_licenca_db_config(request)
        if not banco:
            return {}
        
        empresa = getattr(request.user, 'usua_empr', 1)
        filial = getattr(request.user, 'usua_fili', 1)
        
        # Cache key
        cache_key = f"telas_usuario_{banco}_{empresa}_{filial}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        from .models import PermissaoTela
        permissoes = PermissaoTela.objects.using(banco).filter(
            perm_empr=empresa,
            perm_fili=filial,
            perm_ativ=True
        ).select_related('perm_tela', 'perm_oper', 'perm_tela__tela_modu')
        
        telas_liberadas = {}
        for permissao in permissoes:
            tela_codigo = permissao.perm_tela.tela_codigo
            operacao_codigo = permissao.perm_oper.oper_codigo
            
            if tela_codigo not in telas_liberadas:
                telas_liberadas[tela_codigo] = {
                    'nome': permissao.perm_tela.tela_nome,
                    'modulo': permissao.perm_tela.tela_modu.modu_nome,
                    'operacoes': []
                }
            
            telas_liberadas[tela_codigo]['operacoes'].append(operacao_codigo)
        
        # Cache por 5 minutos
        cache.set(cache_key, telas_liberadas, 300)
        return telas_liberadas
        
    except Exception as e:
        logger.error(f"Erro ao obter telas do usuário: {e}")
        return {}

def get_configuracoes_empresa(request):
    """Retorna todas as configurações da empresa"""
    try:
        banco = get_licenca_db_config(request)
        if not banco:
            return {}
        
        empresa = getattr(request.user, 'usua_empr', 1)
        filial = getattr(request.user, 'usua_fili', 1)
        
        # Cache key
        cache_key = f"config_empresa_{banco}_{empresa}_{filial}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        from .models import ConfiguracaoEstoque, ConfiguracaoFinanceiro
        
        configuracao = {
            'modulos': get_modulos_usuario(request),
            'telas': get_telas_usuario(request)
        }
        
        # Configurações de estoque
        try:
            estoque_config = ConfiguracaoEstoque.objects.using(banco).get(
                conf_empr=empresa,
                conf_fili=filial
            )
            configuracao['estoque'] = {
                'pedidos_movimentam': estoque_config.conf_pedi_move_esto,
                'orcamentos_movimentam': estoque_config.conf_orca_move_esto,
                'os_movimenta': estoque_config.conf_os_move_esto,
                'producao_movimenta': estoque_config.conf_prod_move_esto,
                'permite_negativo': estoque_config.conf_esto_nega,
                'controle_minimo': estoque_config.conf_esto_mini,
                'controle_maximo': estoque_config.conf_esto_maxi,
                'custo_medio': estoque_config.conf_custo_medio,
                'custo_ultimo': estoque_config.conf_custo_ulti
            }
        except ConfiguracaoEstoque.DoesNotExist:
            configuracao['estoque'] = {}
        
        # Configurações financeiras
        try:
            financeiro_config = ConfiguracaoFinanceiro.objects.using(banco).get(
                conf_empr=empresa,
                conf_fili=filial
            )
            configuracao['financeiro'] = {
                'permite_desconto': financeiro_config.conf_perm_desc_pedi,
                'desconto_maximo': float(financeiro_config.conf_desc_maxi_pedi),
                'permite_acrescimo': financeiro_config.conf_perm_acre_pedi,
                'permite_prazo': financeiro_config.conf_perm_vend_praz,
                'prazo_maximo': financeiro_config.conf_praz_maxi_vend,
                'comissao_automatica': financeiro_config.conf_calc_comi_auto,
                'comissao_desconto': financeiro_config.conf_comi_sobr_desc
            }
        except ConfiguracaoFinanceiro.DoesNotExist:
            configuracao['financeiro'] = {}
        
        # Cache por 5 minutos
        cache.set(cache_key, configuracao, 300)
        return configuracao
        
    except Exception as e:
        logger.error(f"Erro ao obter configurações da empresa: {e}")
        return {}

def validar_operacao_estoque(request, operacao, quantidade=None, produto=None):
    """Valida se uma operação de estoque pode ser realizada"""
    try:
        if not verificar_permissao_estoque(request, operacao):
            return False, f"Operação {operacao} não permitida"
        
        # Validações específicas
        if operacao in ['pedido_movimenta', 'os_movimenta', 'producao_movimenta']:
            if not verificar_permissao_estoque(request, 'estoque_negativo'):
                # Verificar se há estoque suficiente
                if produto and quantidade:
                    from Produtos.models import SaldoProduto
                    banco = get_licenca_db_config(request)
                    empresa = getattr(request.user, 'usua_empr', 1)
                    filial = getattr(request.user, 'usua_fili', 1)
                    
                    try:
                        saldo = SaldoProduto.objects.using(banco).get(
                            saldo_empr=empresa,
                            saldo_fili=filial,
                            saldo_prod=produto
                        )
                        if saldo.saldo_estoque < quantidade:
                            return False, f"Estoque insuficiente. Disponível: {saldo.saldo_estoque}"
                    except SaldoProduto.DoesNotExist:
                        return False, "Produto não encontrado no estoque"
        
        return True, "Operação permitida"
        
    except Exception as e:
        logger.error(f"Erro ao validar operação de estoque: {e}")
        return False, f"Erro interno: {str(e)}"

def validar_operacao_financeiro(request, operacao, valor=None, desconto=None):
    """Valida se uma operação financeira pode ser realizada"""
    try:
        if not verificar_permissao_financeiro(request, operacao):
            return False, f"Operação {operacao} não permitida"
        
        # Validações específicas
        if operacao == 'desconto_pedido' and desconto:
            desconto_maximo = get_desconto_maximo(request)
            if desconto > desconto_maximo:
                return False, f"Desconto máximo permitido: {desconto_maximo}%"
        
        return True, "Operação permitida"
        
    except Exception as e:
        logger.error(f"Erro ao validar operação financeira: {e}")
        return False, f"Erro interno: {str(e)}"

def get_modulos_liberados_empresa(banco, empresa_id, filial_id):
    """
    Busca módulos liberados para uma empresa/filial específica no banco de dados
    """
    try:
        from .models import PermissaoModulo
        
        # Buscar permissões ativas para a empresa/filial
        permissoes = PermissaoModulo.objects.using(banco).filter(
            perm_empr=empresa_id,
            perm_fili=filial_id,
            perm_ativ=True
        ).select_related('perm_modu')
        
        # Retornar lista de nomes dos módulos liberados
        modulos_liberados = []
        for permissao in permissoes:
            if permissao.perm_modu.modu_ativ:  # Verificar se o módulo está ativo
                modulos_liberados.append(permissao.perm_modu.modu_nome)
        
        return modulos_liberados
        
    except Exception as e:
        logger.error(f"Erro ao buscar módulos liberados para empresa {empresa_id}/filial {filial_id}: {e}")
        return []

def get_modulos_sistema():
    """
    Retorna todos os módulos do sistema
    """
    try:
        from .models import Modulo
        modulos = Modulo.objects.filter(modu_ativ=True).order_by('modu_ordem', 'modu_nome')
        return [
            {
                'modu_codi': modulo.modu_codi,
                'modu_nome': modulo.modu_nome,
                'modu_desc': modulo.modu_desc,
                'modu_icone': modulo.modu_icone,
                'modu_ordem': modulo.modu_ordem
            }
            for modulo in modulos
        ]
    except Exception as e:
        logger.error(f"Erro ao buscar módulos do sistema: {e}")
        return []

def get_modulo_by_name(nome_modulo):
    """
    Busca um módulo pelo nome
    """
    try:
        from .models import Modulo
        return Modulo.objects.get(modu_nome=nome_modulo, modu_ativ=True)
    except Modulo.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar módulo {nome_modulo}: {e}")
        


def get_modulos_com_status(banco, empresa_id, filial_id):
    """
    Retorna todos os módulos com permissão registrada,
    apenas para módulos ativos no sistema, e se estão ativos (perm_ativ=True).
    """
    permissoes = PermissaoModulo.objects.using(banco).filter(
        perm_empr=empresa_id,
        perm_fili=filial_id
    ).select_related('perm_modu')

    lista = []
    for perm in permissoes:
        modulo = perm.perm_modu
     
        if modulo.modu_ativ:  
            lista.append({
                'nome': modulo.modu_nome,
                'descricao': modulo.modu_desc,
                'icone': modulo.modu_icon,
                'ativo': perm.perm_ativ
            })
    pprint(lista)
    return lista
    



def get_modulos_liberados(banco, empresa_id, filial_id):
    """
    Retorna apenas os módulos com perm_ativ=True
    """
    modulos_com_status = get_modulos_com_status(banco, empresa_id, filial_id)
    pprint(modulos_com_status)
    return [modulo for modulo in modulos_com_status if modulo['ativo']]