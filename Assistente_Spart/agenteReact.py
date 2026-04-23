import logging
from functools import lru_cache
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

# ===== IMPORTAÇÕES DAS TOOLS =====
from .tools.db_tool import (
    cadastrar_produtos, 
    consultar_saldo, 
    consulta_inteligente_prime, 
    consultar_titulos_a_pagar, 
    consultar_titulos_a_receber,
    historico_de_pedidos,
    historico_de_pedidos_cliente,
    total_pedidos_periodo,
    criar_pedido_de_venda,
)
from .tools.file_tool import ler_documentos
from .tools.tool_mapa_semantico import plotar_mapa_semantico
from .tools.rag_tool import rag_url_resposta_vetorial
from .tools.web_tool import procura_web
from .tools.intencao_tool import executar_intencao


# ===== TOOLS VALIDADAS =====
AGENT_TOOLS = [
    executar_intencao,
    cadastrar_produtos,
    consultar_saldo,
    historico_de_pedidos,
    historico_de_pedidos_cliente,
    total_pedidos_periodo,
    consultar_titulos_a_pagar,
    consultar_titulos_a_receber,
    consulta_inteligente_prime,
    ler_documentos,
    plotar_mapa_semantico,
    rag_url_resposta_vetorial,
    procura_web,
    criar_pedido_de_venda,
]

# Validação das tools
for tool in AGENT_TOOLS:
    if not hasattr(tool, 'name'):
        logger.warning(f"⚠️ Tool sem nome: {tool}")
    if not hasattr(tool, 'func'):
        logger.warning(
            f"⚠️ Tool sem função: {tool.name if hasattr(tool, 'name') else tool}"
        )

logger.info(f"✅ {len(AGENT_TOOLS)} tools carregadas")

# ===== SYSTEM PROMPT OTIMIZADO =====
SYSTEM_PROMPT = """Você é um assistente de ERP especializado.

🎯 ESTRATÉGIA DE EXECUÇÃO:
1. Use 'executar_intencao' como PRIMEIRA OPÇÃO - ela roteia para a tool correta
2. Se necessário, chame tools específicas diretamente
3. NUNCA chame ferramentas de contexto (FAISS/RAG) - já está no prompt
4. Execute NO MÁXIMO 1 ferramenta por pergunta

📋 TOOLS DISPONÍVEIS:
- executar_intencao: Roteador inteligente (USE PRIMEIRO)
- cadastrar_produtos
- consultar_saldo
- historico_de_pedidos
- historico_de_pedidos_cliente
- total_pedidos_periodo
- consultar_titulos_a_pagar
- consultar_titulos_a_receber
- consulta_inteligente_prime
- criar_pedido_de_venda
- ler_documentos
- plotar_mapa_semantico
- rag_url_resposta_vetorial
- procura_web

🚫 REGRAS CRÍTICAS:
1. Sempre retorne uma resposta, mesmo se a tool falhar
2. Se houver erro, informe ao usuário de forma clara
3. Respostas concisas
4. Valide parâmetros antes de chamar uma tool
5. Consultas de histórico → prefira historico_de_pedidos_cliente quando aplicável
6. Criar pedidos → prefira criar_pedido_de_venda quando aplicável
7. Peça sempre informações completas para criar pedidos:
    código do cliente ou nome completo.
    data do pedido, ou fale que será criado com data atual.
    itens do pedido, com código do produto, quantidade e preço unitário. 


📍 Contexto da sessão:
- Banco: {banco}
- Empresa: {empresa_id}
- Filial: {filial_id}
"""

# ===== CONFIGURAÇÃO DO LLM =====
llm = ChatOpenAI(
    model="gpt-5.4-mini",
    temperature=0.1,
    max_tokens=2000,
    timeout=30,
    max_retries=2
)

# ===== CONFIGURAÇÃO DE MEMÓRIA =====
memory = MemorySaver()

# ===== CRIAÇÃO DO AGENTE COM ERROR HANDLING =====
try:
    agenteReact = create_react_agent(
        llm,
        AGENT_TOOLS,
        prompt=SYSTEM_PROMPT,
        checkpointer=memory,
    )
    logger.info("✅ Agente React criado com sucesso")

except Exception as e:
    logger.error(f"❌ Erro crítico ao criar agente: {e}")
    raise RuntimeError(f"Falha na inicialização do agente: {e}")

# ===== CACHE DE FAISS =====
@lru_cache(maxsize=200)
def faiss_cached(pergunta: str) -> str:
    """Cache de consultas FAISS."""
    from .tools.qa_tools import faiss_context_qa
    try:
        resultado = faiss_context_qa.invoke({"pergunta": pergunta})
        return str(resultado) if resultado else ""
    except Exception as e:
        logger.warning(f"[CACHE_FAISS] Erro: {e}")
        return ""

# ===== PRÉ-ROTEADOR =====
def pre_rotear(mensagem: str) -> dict:
    """Roteamento ultra-rápido."""
    import re
    msg_lower = mensagem.lower()

    PADROES_DIRETOS = [
        r"produto\s+.+\s+ncm\s+\d+",
        r"saldo\s+(do\s+)?produto\s+\d+",
        r"c[oó]digo\s+\d+",
        r"t[ií]tulo.*?(pagar|receber)",
        r"hist[oó]rico\s+de\s+pedidos",
        r"hist[oó]rico.*cliente",
        r"relat[óo]rio\s+de\s+pedidos",
        r"pedidos\s+por\s+cliente",
    ]

    for padrao in PADROES_DIRETOS:
        if re.search(padrao, msg_lower):
            return {"tipo": "direto", "precisa_faiss": False, "confianca": 0.95}

    PADROES_CONTEXTO = [
        r"como\s+(fa[çc]o|posso)",
        r"o\s+que\s+[ée]",
        r"qual\s+(a|o)",
        r"tutorial|manual",
    ]

    for padrao in PADROES_CONTEXTO:
        if re.search(padrao, msg_lower):
            return {"tipo": "contexto", "precisa_faiss": True, "confianca": 0.90}

    return {"tipo": "geral", "precisa_faiss": True, "confianca": 0.5}


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
                c["tipo"]: round(c["tempo"], 2) for c in self.chamadas
            }
        }

    def limpar(self):
        self.chamadas = []


metricas = MetricasAgente()


# ============================================================
#  WRAPPER FINAL: onde você chama o agente de fato
# ============================================================
def processar_mensagem(mensagem: str, contexto: dict):
    """
    1) Fiscal primeiro
    2) Se não for fiscal → agente ReAct
    """
    # --- camada fiscal ---
    resposta_fiscal = fiscal_pre_handle(mensagem)
    if resposta_fiscal:
        return resposta_fiscal

    # --- camada ReAct normal ---
    resposta = agenteReact.invoke({
        "input": mensagem,
        **contexto
    })
    return resposta
