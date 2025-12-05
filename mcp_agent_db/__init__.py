
"""
MCP Agent DB - Ferramenta de consulta de bases de dados usando linguagem natural
"""

__version__ = "1.0.3"
__author__ = "Leonardo Sousa"
__email__ = "leokaique7@gmail.com"

# Não importar funções que dependem do Django durante a inicialização
# As importações serão feitas quando necessário nas views

__all__ = [
    'consultar_banco_dados',
    'consulta_postgres_tool', 
    'processar_pergunta_com_agente_v2'
]

def get_consultar_banco_dados():
    """Importação lazy da função consultar_banco_dados"""
    from .consulta_tool import consultar_banco_dados
    return consultar_banco_dados

def get_processar_pergunta_com_agente_v2():
    """Importação lazy da função processar_pergunta_com_agente_v2"""
    from .agente_inteligente_v2 import processar_pergunta_com_agente_v2
    return processar_pergunta_com_agente_v2
default_app_config = 'mcp_agent_db.apps.McpAgentDbConfig'
