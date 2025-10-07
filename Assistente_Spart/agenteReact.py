from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from .configuracoes.config import CHAT_MODEL
from .tools.intencao_tool import identificar_intencao, executar_intencao
from .tools.db_tool import cadastrar_produtos, consultar_saldo
from .tools.rag_tool import rag_url_resposta_vetorial
from .tools.inspector_tools import inspector_faiss, rag_url_resposta
from .tools.qa_tools import faiss_condicional_qa
from .tools.dataset_tools import salvar_dataset_finetuning
from .tools.tool_mapa_semantico import plotar_mapa_semantico



llm = ChatOpenAI(model=CHAT_MODEL, temperature=0)  # O prompt é injetado pelo caller (views) com contexto de empresa/filial/banco
memoria = MemorySaver()

agenteReact = create_react_agent(
    llm,
    tools=[identificar_intencao, executar_intencao, cadastrar_produtos, consultar_saldo, rag_url_resposta_vetorial, inspector_faiss, rag_url_resposta, faiss_condicional_qa, salvar_dataset_finetuning, plotar_mapa_semantico],
    checkpointer=memoria
)
