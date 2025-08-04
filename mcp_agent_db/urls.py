from django.urls import path
from .views import (
    consulta_view, 
    consulta_streaming_view, 
    health_check,
    historico_view,
    limpar_cache_view,
    limpar_historico_view,
    list_schemas,
    grafico_view,
    docs_view
)

urlpatterns = [
    # Interface web
    path('docs/', docs_view, name='mcp-docs'),
    
    # API endpoints
    path('health/', health_check, name='mcp-health'),
    path('schemas/', list_schemas, name='mcp-schemas'),
    path('consulta/', consulta_view, name='mcp-consulta'),
    path('consulta-streaming/', consulta_streaming_view, name='mcp-consulta-streaming'),
    path('grafico/', grafico_view, name='mcp-grafico'),
    path('historico/', historico_view, name='mcp-historico'),    
    path('limpar-cache/', limpar_cache_view, name='mcp-limpar-cache'),
    path('limpar-historico/', limpar_historico_view, name='mcp-limpar-historico'),       
]