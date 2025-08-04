from typing import List, Dict, Any
from langgraph.prebuilt import create_react_agent
from langchain.prompts import PromptTemplate
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langchain.memory import ConversationBufferMemory
from langgraph.checkpoint.memory import MemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient
from .mcp_servers import MCP_SERVERS_CONFIG
from .sql_generator import gerar_sql_da_pergunta
from dotenv import load_dotenv
from .consulta_tool import consulta_postgres_tool, consultar_banco_dados
import asyncio
import os
from .cache_manager import query_cache
from .conversation_memory import conversation_memory
from .django_adapter import DjangoMCPAdapter

load_dotenv()

# Remover django.setup() - será configurado pelo Django automaticamente
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
# django.setup()

# Inicializar componentes globais
model_llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")
memory = ConversationBufferMemory(memory_key="chat_history")
memory_saver = MemorySaver()

mcp_client = None
agent_executor = None

def validar_schema_ferramenta(tool) -> bool:
    """Valida se o schema da ferramenta é compatível com Gemini"""
    try:
        # Lista de ferramentas conhecidas como problemáticas
        ferramentas_problematicas = [
            'generate_fishbone_diagram',
            'generate_mind_map', 
            'generate_organization_chart',
            'generate_word_cloud_chart',
            'generate_flow_diagram',
            'generate_network_graph'
        ]
        
        # Rejeitar ferramentas conhecidas como problemáticas
        if tool.name in ferramentas_problematicas:
            return False
        
        # Verificar se a ferramenta tem schema
        if not hasattr(tool, 'args_schema') or tool.args_schema is None:
            return True
        
        # Converter schema para dict para análise
        try:
            schema_dict = tool.args_schema.model_json_schema() if hasattr(tool.args_schema, 'model_json_schema') else {}
        except Exception:
            return False
        
        # Verificar se há propriedades recursivas problemáticas
        def verificar_recursao(obj, profundidade=0):
            if profundidade > 3:  # Limite de profundidade mais restritivo
                return False
            
            if isinstance(obj, dict):
                # Verificar se há chave '$schema' problemática
                if '$schema' in obj:
                    return False
                    
                if 'properties' in obj:
                    for prop_name, prop_value in obj['properties'].items():
                        if isinstance(prop_value, dict):
                            # Verificar estruturas recursivas específicas
                            if 'items' in prop_value and isinstance(prop_value['items'], dict):
                                if 'properties' in prop_value['items']:
                                    # Verificar se há 'children' recursivos
                                    if 'children' in prop_value['items']['properties']:
                                        children_prop = prop_value['items']['properties']['children']
                                        if isinstance(children_prop, dict) and 'items' in children_prop:
                                            return False
                            
                            # Verificar recursivamente
                            if not verificar_recursao(prop_value, profundidade + 1):
                                return False
                                
                if 'items' in obj and isinstance(obj['items'], dict):
                    if not verificar_recursao(obj['items'], profundidade + 1):
                        return False
            
            return True
        
        return verificar_recursao(schema_dict)
        
    except Exception as e:
        print(f"⚠️ Erro ao validar schema da ferramenta {tool.name}: {e}")
        return False

def filtrar_ferramentas_validas(mcp_tools: List) -> List:
    """Filtra ferramentas MCP com schemas válidos - APENAS whitelist restrita"""
    ferramentas_validas = []
    ferramentas_removidas = []
    
    # Lista MUITO restrita de ferramentas básicas e seguras
    ferramentas_seguras = [
        'generate_bar_chart',
        'generate_pie_chart', 
        'generate_line_chart',
        'generate_column_chart'
    ]
    
    for tool in mcp_tools:
        # Usar APENAS whitelist - não validar outras
        if tool.name in ferramentas_seguras:
            ferramentas_validas.append(tool)
        else:
            ferramentas_removidas.append(tool.name)
    
    if ferramentas_removidas:
        print(f"⚠️ Ferramentas removidas (whitelist restrita): {len(ferramentas_removidas)} ferramentas")
    
    print(f"✅ Ferramentas válidas mantidas: {', '.join([t.name for t in ferramentas_validas])}")
    
    return ferramentas_validas

async def inicializar_agente():
    """Inicializa o agente com MCP client de forma assíncrona"""
    global mcp_client, agent_executor
    
    try:
        print("🔄 Inicializando MCP Client... ", MCP_SERVERS_CONFIG)
        
        # Obter contexto da empresa atual
        contexto = DjangoMCPAdapter.get_empresa_context()
        print(f"🏢 Contexto da empresa: {contexto}")
        
        # Inicializar MCP Client com a configuração correta
        mcp_client = MultiServerMCPClient(MCP_SERVERS_CONFIG)
        
        # Obter ferramentas do MCP client
        mcp_tools_raw = await mcp_client.get_tools()
        print(f"✅ {len(mcp_tools_raw)} ferramentas MCP obtidas")
        
        # Filtrar ferramentas com schemas válidos
        mcp_tools = filtrar_ferramentas_validas(mcp_tools_raw)
        print(f"✅ {len(mcp_tools)} ferramentas MCP válidas carregadas")
        
        # Listar ferramentas disponíveis
        for tool in mcp_tools:
            print(f"🔧 Ferramenta MCP: {tool.name}")
        
        print("🔄 Criando agente...")
        
        # Criar prompt personalizado com contexto da empresa
        system_prompt = f"""Você é um analista de dados especializado em sistemas de gestão empresarial com capacidade de gerar visualizações.

CONTEXTO DA EMPRESA:
- Empresa: {contexto.get('empresa', 'N/A')}
- Slug: {contexto.get('slug', 'N/A')}
- Módulos disponíveis: {len(contexto.get('modulos_disponiveis', []))}

INSTRUÇÕES CRÍTICAS:
1. Para perguntas sobre DADOS: use a ferramenta consultar_banco_dados
2. Para perguntas sobre GRÁFICOS: use as ferramentas MCP disponíveis para gerar gráficos
3. Faça APENAS UMA chamada da ferramenta por pergunta
4. NÃO tente múltiplas variações ou reformulações
5. NÃO pergunte detalhes ao usuário - os metadados já contêm as informações necessárias

FERRAMENTAS DISPONÍVEIS:
- consultar_banco_dados: Para consultas de dados do PostgreSQL
- Ferramentas MCP: Para criar gráficos interativos (generate_bar_chart, generate_pie_chart, etc.)

DETECÇÃO DE SOLICITAÇÕES DE GRÁFICO:
Se a pergunta contém palavras como: "gráfico", "grafico", "chart", "visualiza", "gere um gráfico", "criar gráfico"
→ Use as ferramentas MCP de gráficos disponíveis

METADADOS DISPONÍVEIS:
- Campo enti_tipo_enti na tabela entidades (CL=Cliente, VE=Vendedor, FO=Fornecedor)
- Tabelas: entidades, pedidosvenda, produtos, funcionarios
- Relacionamentos já mapeados nos metadados

FLUXO PARA GRÁFICOS:
1. Primeiro obtenha os dados com consultar_banco_dados
2. Depois use a ferramenta MCP apropriada
3. Formate os dados no padrão esperado pela ferramenta MCP

TIPOS DE GRÁFICO DISPONÍVEIS:
- generate_bar_chart: Gráfico de barras (padrão)
- generate_pie_chart: Gráfico de pizza
- generate_line_chart: Gráfico de linhas
- generate_column_chart: Gráfico de colunas

SEMPRE responda em português brasileiro e seja DIRETO."""

        # Incluir ferramentas MCP nas ferramentas do agente
        todas_ferramentas = [consultar_banco_dados, consulta_postgres_tool] + mcp_tools

        agent_executor = create_react_agent(
            model=model_llm,
            tools=todas_ferramentas,
            checkpointer=memory_saver,
            state_modifier=system_prompt
        )
        
        print("✅ Agente inicializado com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao inicializar agente: {e}")
        return False

def processar_pergunta_com_agente_v2(pergunta: str, user=None) -> str:
    """Processa pergunta usando o agente v2 com contexto Django"""
    try:
        # Log da atividade
        if user:
            DjangoMCPAdapter.log_atividade(user, "CONSULTA", {"pergunta": pergunta})
        
        # Obter contexto da empresa
        contexto = DjangoMCPAdapter.get_empresa_context()
        
        # Adicionar contexto à pergunta se necessário
        pergunta_com_contexto = f"[Empresa: {contexto.get('empresa', 'N/A')}] {pergunta}"
        
        # Verificar se o agente está inicializado
        if agent_executor is None:
            # Tentar inicializar de forma síncrona
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            sucesso = loop.run_until_complete(inicializar_agente())
            loop.close()
            
            if not sucesso:
                return "❌ Erro: Não foi possível inicializar o agente inteligente."
        
        # Executar o agente
        config = {"configurable": {"thread_id": f"thread_{contexto.get('slug', 'default')}"}}
        
        resultado = agent_executor.invoke(
            {"messages": [("user", pergunta_com_contexto)]},
            config=config
        )
        
        # Extrair resposta
        if "messages" in resultado and resultado["messages"]:
            ultima_mensagem = resultado["messages"][-1]
            if hasattr(ultima_mensagem, 'content'):
                resposta = ultima_mensagem.content
            else:
                resposta = str(ultima_mensagem)
        else:
            resposta = "Não foi possível obter uma resposta do agente."
        
        # Adicionar ao histórico
        conversation_memory.add_interaction(pergunta, resposta, contexto.get('empresa'))
        
        return resposta
        
    except Exception as e:
        erro_msg = f"❌ Erro ao processar pergunta: {str(e)}"
        print(erro_msg)
        return erro_msg

def processar_pergunta_com_streaming_sync(pergunta: str) -> dict:
    """Versão síncrona para streaming"""
    try:
        resposta = processar_pergunta_com_agente_v2(pergunta)
        return {
            "pergunta": pergunta,
            "resposta": resposta,
            "status": "sucesso",
            "etapas_executadas": 5
        }
    except Exception as e:
        return {
            "pergunta": pergunta,
            "resposta": f"Erro: {str(e)}",
            "status": "erro",
            "etapas_executadas": 0
        }

def gerar_sql(pergunta: str, slug: str = "casaa") -> str:
    """Função auxiliar para gerar SQL"""
    return gerar_sql_da_pergunta(pergunta, slug)

# Inicializar agente na importação (opcional)
if __name__ == "__main__":
    print("🚀 Testando inicialização do agente...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    sucesso = loop.run_until_complete(inicializar_agente())
    loop.close()
    if sucesso:
        print("✅ Agente pronto para uso!")
    else:
        print("⚠️ Agente em modo fallback")