import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from .tools.db_tool import cadastrar_produtos, consultar_saldo
from .tools.file_tool import ler_documentos
from .tools.inspector_tools import rag_url_resposta, inspector_faiss
from .tools.intencao_tool import identificar_intencao, executar_intencao, consulta_inteligente_prime
from .tools.qa_tools import faiss_context_qa, faiss_condicional_qa
from .tools.tool_mapa_semantico import plotar_mapa_semantico
from .tools.rag_tool import rag_url_resposta_vetorial
from .tools.web_tool import procura_web

logger = logging.getLogger(__name__)

AGENT_TOOLS = [
    identificar_intencao,
    executar_intencao,
    cadastrar_produtos,
    consultar_saldo,
    consulta_inteligente_prime,
    ler_documentos,
    rag_url_resposta,
    rag_url_resposta_vetorial,
    inspector_faiss,
    faiss_context_qa,
    faiss_condicional_qa,
    plotar_mapa_semantico,
    procura_web,
]

# System prompt
SYSTEM_PROMPT = """Você é um agente especialista em ERP multiempresa e marketplace.
Entenda a intenção do usuário (consultar saldo, cadastrar produto, gerar relatório, etc.)
e acione as ferramentas adequadas automaticamente.

Siga as regras:
- Use 'identificar_intencao' e depois 'executar_intencao'.
- Utilize o banco, empresa e filial passados no contexto configurável.
- Nunca invente dados; consulte as ferramentas.
- Responda sempre em português, de forma técnica e direta."""

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, streaming=True)

# Usando LangGraph para melhor suporte a streaming e estado
agenteReact = create_react_agent(
    llm,
    tools=AGENT_TOOLS,
    state_modifier=SYSTEM_PROMPT,
    checkpointer=MemorySaver()
)