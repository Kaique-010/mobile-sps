"""
Adaptador para integrar o MCP Agent DB com o sistema Django
"""
import os
import django
from django.conf import settings
from core.middleware import get_licenca_slug, get_modulos_disponiveis
from core.utils import get_licenca_db_config

# Não configurar Django aqui - será configurado automaticamente
# if not settings.configured:
#     os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
#     django.setup()

class DjangoMCPAdapter:
    """Adaptador para integrar MCP Agent com Django"""
    
    @staticmethod
    def get_empresa_context():
        """Obtém contexto da empresa atual baseado no slug"""
        slug = get_licenca_slug()
        modulos = get_modulos_disponiveis()
        
        return {
            'slug': slug,
            'empresa': slug,
            'modulos_disponiveis': modulos or [],
            'tem_acesso_ia': True  # Por enquanto permitir a todos
        }
    
    @staticmethod
    def get_database_config():
        """Obtém configuração do banco de dados para a empresa atual"""
        try:
            from django.db import connection
            
            # Usar a conexão Django padrão
            db_config = {
                'host': connection.settings_dict['HOST'],
                'port': connection.settings_dict['PORT'],
                'database': connection.settings_dict['NAME'],
                'user': connection.settings_dict['USER'],
                'password': connection.settings_dict['PASSWORD'],
            }
            
            return db_config
            
        except Exception as e:
            print(f"Erro ao obter configuração do banco: {e}")
            return None
    
    @staticmethod
    def verificar_permissoes(user, modulo='mcp_agent'):
        """Verifica se o usuário tem permissões para usar o módulo"""
        if not user or not user.is_authenticated:
            return False
        
        # Por enquanto, permitir acesso a usuários autenticados
        # Você pode implementar lógica mais específica aqui
        modulos = get_modulos_disponiveis()
        
        # Se não há módulos definidos, permitir acesso
        if not modulos:
            return True
        
        # Verificar se tem acesso específico ao módulo
        return modulo in modulos or 'relatorios_ia' in modulos or 'admin' in modulos
    
    @staticmethod
    def log_atividade(user, acao, detalhes=None):
        """Log de atividades do usuário no MCP Agent"""
        try:
            from auditoria.models import LogAuditoria
            
            slug = get_licenca_slug()
            
            LogAuditoria.objects.create(
                usuario=user.usua_nome if user else 'anonimo',
                acao=f"MCP_AGENT_{acao}",
                detalhes=detalhes or {},
                empresa=slug,
                ip_address=None  # Você pode capturar o IP se necessário
            )
            
        except Exception as e:
            print(f"Erro ao registrar log de auditoria: {e}")