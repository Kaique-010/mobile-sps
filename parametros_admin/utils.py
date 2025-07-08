from .models import LogParametros
from core.utils import get_licenca_db_config
import json
import logging
from parametros_admin.models import ParametrosGerais

logger = logging.getLogger(__name__)

def log_alteracao(tabela, registro_id, acao, valor_anterior, valor_novo, usuario, ip=None):
    """Registra alteração nos logs"""
    try:
        # Usar banco padrão para logs (ou você pode usar o mesmo banco da licença)
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

def log_alteracao_detalhada(tabela, registro_id, acao, valor_anterior, valor_novo, usuario, ip=None, detalhes=None):
    """Sistema de log mais detalhado"""
    try:
        log_data = {
            'log_tabe': tabela,
            'log_regi': registro_id,
            'log_acao': acao,
            'log_valo_ante': json.dumps(valor_anterior, ensure_ascii=False) if valor_anterior else '',
            'log_valo_novo': json.dumps(valor_novo, ensure_ascii=False) if valor_novo else '',
            'log_usua': usuario,
            'log_ip': ip,
            'log_detalhes': json.dumps(detalhes, ensure_ascii=False) if detalhes else ''
        }
        
        LogParametros.objects.create(**log_data)
        
        # Log também no arquivo para backup
        logger.info(f"LOG_PARAMETROS: {acao} em {tabela}#{registro_id} por {usuario}")
        
    except Exception as e:
        logger.error(f"Erro ao registrar log detalhado: {e}")

def get_parametro(request, nome_parametro, default=None):
    """Obtém valor de um parâmetro específico"""
    parametros = getattr(request, 'parametros_gerais', {})
    return parametros.get(nome_parametro, default)

def verificar_permissao_estoque(request, operacao):
    """Verifica se uma operação de estoque é permitida"""
    config = getattr(request, 'estoque_config', {})
    
    mapeamento = {
        'pedido': 'pedidos_movimentam',
        'orcamento': 'orcamentos_movimentam',
        'os': 'os_movimenta',
        'producao': 'producao_movimenta'
    }
    
    return config.get(mapeamento.get(operacao), True)

def verificar_permissao_financeiro(request, operacao):
    """Verifica se uma operação financeira é permitida"""
    config = getattr(request, 'financeiro_config', {})
    
    mapeamento = {
        'desconto': 'permite_desconto_pedido',
        'acrescimo': 'permite_acrescimo_pedido',
        'prazo': 'permite_vendas_prazo'
    }
    
    return config.get(mapeamento.get(operacao), True)

def get_desconto_maximo(request):
    """Retorna o desconto máximo permitido"""
    config = getattr(request, 'financeiro_config', {})
    return config.get('desconto_maximo_pedido', 0.0)

def limpar_cache_configuracoes(banco=None):
    """Limpa cache de configurações"""
    from django.core.cache import cache
    
    if banco:
        cache.delete(f"estoque_config_{banco}")
        cache.delete(f"financeiro_config_{banco}")
        cache.delete(f"parametros_gerais_{banco}")
    else:
        # Limpar todos os caches relacionados
        cache.delete_many([
            key for key in cache._cache.keys() 
            if any(prefix in key for prefix in ['estoque_config_', 'financeiro_config_', 'parametros_gerais_'])
        ])


def get_modulos_sistema():
    """Busca todos os módulos disponíveis no sistema"""
    import os
    from django.conf import settings
    
    modulos = []
    # Buscar todos os apps Django
    for app in settings.INSTALLED_APPS:
        if not app.startswith('django.') and not app.startswith('rest_framework'):
            app_name = app.split('.')[-1]
            modulos.append({
                'codigo': app_name,
                'nome': app_name.replace('_', ' ').title(),
                'descricao': f'Módulo {app_name}'
            })
    
    return modulos

def get_modulos_empresa(request, empresa_id, filial_id):
    """Retorna módulos liberados para uma empresa específica"""
    from .models import PermissoesModulos
    banco = get_licenca_db_config(request)
    
    modulos_liberados = PermissoesModulos.objects.using(banco).filter(
        perm_empr=empresa_id,
        perm_fili=filial_id,
        perm_ativ=True
    ).values_list('perm_modu', flat=True)
    
    return list(modulos_liberados)


def get_telas_sistema():
    """Lista todas as telas/componentes do frontend"""
    # Estas seriam as telas do seu frontend React
    return [
        {'codigo': 'pedidos_lista', 'nome': 'Lista de Pedidos', 'modulo': 'Pedidos'},
        {'codigo': 'pedidos_form', 'nome': 'Formulário de Pedidos', 'modulo': 'Pedidos'},
        {'codigo': 'produtos_lista', 'nome': 'Lista de Produtos', 'modulo': 'Produtos'},
        {'codigo': 'estoque_entrada', 'nome': 'Entrada de Estoque', 'modulo': 'Entradas_Estoque'},
        {'codigo': 'financeiro_dashboard', 'nome': 'Dashboard Financeiro', 'modulo': 'Financeiro'},
        # ... adicionar todas as telas
    ]

def get_telas_sistema_completo():
    """Lista todas as telas do frontend com operações CRUD"""
    telas = [
        # Pedidos
        {'codigo': 'pedidos_lista', 'nome': 'Lista de Pedidos', 'modulo': 'pedidos', 'operacoes': ['read', 'create', 'update', 'delete']},
        {'codigo': 'pedidos_form', 'nome': 'Formulário de Pedidos', 'modulo': 'pedidos', 'operacoes': ['read', 'create', 'update']},
        
        # Produtos
        {'codigo': 'produtos_lista', 'nome': 'Lista de Produtos', 'modulo': 'produtos', 'operacoes': ['read', 'create', 'update', 'delete']},
        {'codigo': 'produtos_form', 'nome': 'Formulário de Produtos', 'modulo': 'produtos', 'operacoes': ['read', 'create', 'update']},
        
        # Estoque
        {'codigo': 'estoque_entrada', 'nome': 'Entrada de Estoque', 'modulo': 'estoque', 'operacoes': ['read', 'create']},
        {'codigo': 'estoque_saida', 'nome': 'Saída de Estoque', 'modulo': 'estoque', 'operacoes': ['read', 'create']},
        
        # Financeiro
        {'codigo': 'contas_receber', 'nome': 'Contas a Receber', 'modulo': 'financeiro', 'operacoes': ['read', 'update']},
        {'codigo': 'contas_pagar', 'nome': 'Contas a Pagar', 'modulo': 'financeiro', 'operacoes': ['read', 'update']},
        
        # Dashboards
        {'codigo': 'dashboard_vendas', 'nome': 'Dashboard Vendas', 'modulo': 'dashboards', 'operacoes': ['read']},
        {'codigo': 'dashboard_financeiro', 'nome': 'Dashboard Financeiro', 'modulo': 'dashboards', 'operacoes': ['read']}
    ]
    
    return telas

def verificar_permissao_tela(request, tela, acao):
    """Verifica se usuário tem permissão para ação específica em uma tela"""
    from .models import PermissoesRotas
    banco = get_licenca_db_config(request)
    
    return PermissoesRotas.objects.using(banco).filter(
        rota_tela=tela,
        rota_acao=acao,
        rota_ativ=True
    ).exists()


def get_modulos_sistema_completo():
    """Busca todos os módulos e telas do sistema automaticamente"""
    import os
    from django.conf import settings
    from django.urls import get_resolver
    
    modulos = []
    
    # Módulos principais do sistema
    modulos_principais = [
        {'codigo': 'pedidos', 'nome': 'Pedidos', 'descricao': 'Gestão de pedidos de venda'},
        {'codigo': 'produtos', 'nome': 'Produtos', 'descricao': 'Cadastro de produtos'},
        {'codigo': 'estoque', 'nome': 'Estoque', 'descricao': 'Controle de estoque'},
        {'codigo': 'financeiro', 'nome': 'Financeiro', 'descricao': 'Gestão financeira'},
        {'codigo': 'orcamentos', 'nome': 'Orçamentos', 'descricao': 'Orçamentos de venda'},
        {'codigo': 'ordem_servico', 'nome': 'Ordem de Serviço', 'descricao': 'Ordens de serviço'},
        {'codigo': 'contratos', 'nome': 'Contratos', 'descricao': 'Gestão de contratos'},
        {'codigo': 'dashboards', 'nome': 'Dashboards', 'descricao': 'Painéis gerenciais'},
        {'codigo': 'parametros_admin', 'nome': 'Parâmetros Admin', 'descricao': 'Administração do sistema'}
    ]
    
    return modulos_principais