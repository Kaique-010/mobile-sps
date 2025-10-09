import logging
from functools import lru_cache
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

# Tools otimizadas
from .tools.db_tool import cadastrar_produtos, consultar_saldo, consulta_inteligente_prime
from .tools.file_tool import ler_documentos
from .tools.tool_mapa_semantico import plotar_mapa_semantico
from .tools.rag_tool import rag_url_resposta_vetorial
from .tools.web_tool import procura_web

logger = logging.getLogger(__name__)

# ===== IMPORTAR executar_intencao MODIFICADA =====
# CRÍTICO: Vamos modificar ela para NÃO chamar faiss_condicional_qa
# A view já faz isso antes do agente!
from .tools.intencao_tool import executar_intencao

# ===== TOOLS FINAIS (8) =====
AGENT_TOOLS = [
    executar_intencao,          # Roteador principal
    cadastrar_produtos,         
    consultar_saldo,            
    consulta_inteligente_prime, 
    ler_documentos,             
    plotar_mapa_semantico,      
    rag_url_resposta_vetorial,  
    procura_web,                
]

# ===== SYSTEM PROMPT OTIMIZADO =====
SYSTEM_PROMPT = """Você é um assistente de ERP. Estratégia de duas camadas:

🎯 CAMADA 1 - ROTEAMENTO (sempre use primeiro):
'executar_intencao': Roteador inteligente que detecta:
- Cadastros: "produto <nome> ncm <codigo>"
- Saldo: "saldo produto <numero>"
- Perguntas de negócio: vendas, pedidos, clientes
- Documentação: já foi fornecida no contexto acima

⚡ CAMADA 2 - EXECUÇÃO DIRETA (só se necessário):
- cadastrar_produtos, consultar_saldo, etc.

🚫 REGRAS CRÍTICAS:
1. NÃO chame ferramentas de busca de contexto (FAISS/RAG) - o contexto já está no prompt!
2. Execute no MÁXIMO 1 ferramenta por pergunta
3. Se o contexto já tem a resposta, responda diretamente SEM chamar ferramentas
4. Respostas concisas (máximo 200 palavras)

📍 Contexto:
- Banco: {banco}
- Empresa: {empresa_id}
- Filial: {filial_id}"""

# ===== LLM OTIMIZADO =====
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    streaming=True,
    max_tokens=600,  # Reduzido para respostas mais curtas
    timeout=10.0     # Timeout de 10s
)

# ===== AGENTE =====
agenteReact = create_react_agent(
    llm,
    tools=AGENT_TOOLS,
    state_modifier=SYSTEM_PROMPT,
    checkpointer=MemorySaver(),
)

# ===== CACHE DE FAISS =====
@lru_cache(maxsize=200)
def faiss_cached(pergunta: str) -> str:
    """
    Cache de consultas FAISS.
    Chamado ANTES do agente para enriquecer o prompt.
    """
    from .tools.qa_tools import faiss_context_qa
    try:
        resultado = faiss_context_qa.invoke({"pergunta": pergunta})
        return resultado if resultado else ""
    except Exception as e:
        logger.warning(f"[CACHE_FAISS] Erro: {e}")
        return ""


# ===== PRÉ-ROTEADOR =====
def pre_rotear(mensagem: str) -> dict:
    """
    Roteamento ultra-rápido (1ms) para decidir se precisa FAISS.
    """
    import re
    msg_lower = mensagem.lower()
    
    # Padrões DIRETOS (não precisam FAISS)
    PADROES_DIRETOS = [
        r"produto\s+.+\s+ncm\s+\d+",           # Cadastro
        r"saldo\s+(do\s+)?produto\s+\d+",      # Saldo
        r"c[oó]digo\s+\d+",                    # Referência a código
        r"pedido\s+\d+",                       # Pedido específico
    ]
    
    for padrao in PADROES_DIRETOS:
        if re.search(padrao, msg_lower):
            return {
                "tipo": "direto",
                "precisa_faiss": False,
                "confianca": 0.95
            }
    
    # Padrões de CONTEXTO (precisam FAISS)
    PADROES_CONTEXTO = [
        r"como\s+(fa[çc]o|posso|configurar|emitir)",
        r"o\s+que\s+[ée]",
        r"qual\s+(a|o)",
        r"tutorial|instru[çc][ãa]o|manual|documenta[çc][ãa]o",
        r"passo\s+a\s+passo",
    ]
    
    for padrao in PADROES_CONTEXTO:
        if re.search(padrao, msg_lower):
            return {
                "tipo": "contexto",
                "precisa_faiss": True,
                "confianca": 0.90
            }
    
    # Consultas de negócio (podem usar FAISS leve)
    PADROES_NEGOCIO = [
        r"venda|pedido|cliente|nota\s+fiscal|faturamento"
    ]
    
    for padrao in PADROES_NEGOCIO:
        if re.search(padrao, msg_lower):
            return {
                "tipo": "negocio",
                "precisa_faiss": False,  # Usa DB diretamente
                "confianca": 0.85
            }
    
    # Fallback: usa FAISS
    return {
        "tipo": "geral",
        "precisa_faiss": True,
        "confianca": 0.5
    }


# ===== MÉTRICAS =====
class MetricasAgente:
    def __init__(self):
        self.chamadas = []
    
    def registrar(self, tipo: str, tempo: float, tokens: int = 0):
        self.chamadas.append({
            "tipo": tipo,
            "tempo": tempo,
            "tokens": tokens,
            "timestamp": __import__('time').time()
        })
    
    def relatorio(self) -> dict:
        if not self.chamadas:
            return {}
        
        total = sum(c["tempo"] for c in self.chamadas)
        return {
            "total_chamadas": len(self.chamadas),
            "tempo_total": round(total, 2),
            "breakdown": {
                c["tipo"]: round(c["tempo"], 2) 
                for c in self.chamadas
            }
        }
    
    def limpar(self):
        self.chamadas = []

metricas = MetricasAgente()