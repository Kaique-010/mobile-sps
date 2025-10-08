from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from langchain_core.tools import Tool
from .tools import (
    identificar_intencao,
    executar_intencao,
    cadastrar_produtos,
    consultar_saldo,
)

# Define todas as tools disponíveis
AGENT_TOOLS = [
    identificar_intencao,
    executar_intencao,
    cadastrar_produtos,
    consultar_saldo,
]

# Modelo principal
llm = ChatOpenAI(model="gpt-4o", temperature=0)

# Cria o agent com suporte automático a tool-calling
agenteReact_core = create_openai_tools_agent(llm, AGENT_TOOLS)

# Envolve num executor que repete enquanto houver tool_calls
agenteReact = AgentExecutor(
    agent=agenteReact_core,
    tools=AGENT_TOOLS,
    handle_parsing_errors=True,
    verbose=True,
    max_iterations=6,  # evita loops infinitos
)
