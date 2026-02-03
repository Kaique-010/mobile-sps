from django.apps import AppConfig

class McpAgentDbConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mcp_agent_db'
    verbose_name = 'MCP Agent DB'
    
    def ready(self):
        """Inicialização do app quando Django carrega"""
        pass