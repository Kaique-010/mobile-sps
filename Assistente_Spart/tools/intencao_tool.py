from langchain_core.tools import tool
import re
import logging
from core.utils import get_db_from_slug

# Tools de negócio
from .db_tool import (
    cadastrar_produtos,
    consultar_saldo,
    consulta_inteligente_prime,
)
from .rag_tool import rag_url_resposta_vetorial
from .web_tool import procura_web
from .file_tool import ler_documentos
from .tool_mapa_semantico import plotar_mapa_semantico

logger = logging.getLogger(__name__)

@tool
def executar_intencao(
    mensagem: str,
    banco: str = "default",
    slug: str = None,
    empresa_id: str = "1",
    filial_id: str = "1"
) -> str:
    """
    Executa a intenção detectada roteando para a tool adequada.

    MODIFICAÇÃO CRÍTICA: NÃO chama mais faiss_context_qa ou faiss_condicional_qa.
    O contexto FAISS já foi fornecido pela view ANTES do agente!

    Regras principais:
    - Cadastro: "produto <nome> ncm <codigo>" -> cadastrar_produtos
    - Saldo: contém "saldo|estoque|quantidade" e "codigo|produto <número>" -> consultar_saldo
    - Pergunta de negócio (vendas, pedidos, clientes, etc.) -> consulta_inteligente_prime
    - Pergunta sobre URL específica -> rag_url_resposta_vetorial
    - Pesquisa na web (google, web, internet) -> procura_web
    - Leitura de arquivo local (caminho/arquivo) -> ler_documentos
    - Visualização do cérebro semântico (mapa semântico, pca/tsne) -> plotar_mapa_semantico
    - Perguntas gerais/documentação -> CONTEXTO JÁ FORNECIDO, retorna orientação
    """
    try:
        # Determina banco
        if banco and banco != "default":
            real_banco = banco
        elif slug:
            real_banco = get_db_from_slug(slug)
        else:
            real_banco = "default"

        logger.info(f"[EXECUTAR_INTENCAO] Banco: {real_banco} | Empresa: {empresa_id} | Filial: {filial_id}")
        msg_lower = mensagem.lower()

        # ========== INSTRUÇÕES DE USO ==========
        if re.search(r"(?i)como(\s+posso|\s+fa[cç]o)?\s+cadastrar", msg_lower):
            return (
                "Para cadastrar produto, envie: 'produto <nome> ncm <codigo>'.\n"
                "Exemplo: produto Mesa de Jantar ncm 94036000"
            )

        # ========== CADASTRO DE PRODUTO ==========
        m_cad = re.search(r"(?i)produto\s+(.+?)\s+ncm\s+(\d+)", mensagem)
        if m_cad:
            nome = m_cad.group(1).strip()
            ncm = m_cad.group(2).strip()
            logger.info(f"[EXECUTAR_INTENCAO] Cadastro: {nome}, ncm={ncm}")
            return cadastrar_produtos.func(
                prod_nome=nome,
                prod_ncm=ncm,
                banco=real_banco,
                empresa_id=str(empresa_id),
                filial_id=str(filial_id),
            )
        
        if re.search(r"(?i)cadastro|cadastrar|novo\s+produto", msg_lower) and not m_cad:
            return "Para cadastrar, informe: 'produto <nome> ncm <codigo>'"

        # ========== CONSULTA DE SALDO ==========
        m_saldo_kw = re.search(r"(?i)(saldo|estoque|quantidade)", msg_lower)
        m_saldo_cod = re.search(r"(?i)(c[oó]digo|produto)\s+(\d+)", msg_lower)
        if m_saldo_kw and m_saldo_cod:
            codigo = m_saldo_cod.group(2).strip()
            logger.info(f"[EXECUTAR_INTENCAO] Consulta saldo: {codigo}")
            return consultar_saldo.func(
                produto_codigo=codigo,
                banco=real_banco,
                empresa_id=str(empresa_id),
                filial_id=str(filial_id),
            )

        # ========== VISUALIZAÇÃO — MAPA SEMÂNTICO ==========
        if re.search(r"(?i)(mapa\s+sem[aâ]ntico|c[ée]rebro|pca|tsne)", msg_lower):
            metodo = "tsne" if "tsne" in msg_lower else "pca"
            return plotar_mapa_semantico.func(pergunta=mensagem, metodo=metodo)

        # ========== LEITURA DE ARQUIVO LOCAL ==========
        if re.search(r"(?i)(ler|abrir)\s+(arquivo|documento)", msg_lower):
            m_path = re.search(r"(?i)arquivo\s+([\w:\\\/\.\-]+)|['\"]([^'\"]+)['\"]", mensagem)
            file_path = None
            if m_path:
                file_path = m_path.group(1) or m_path.group(2)
            if file_path:
                return ler_documentos.func(file_path=file_path)
            else:
                return "Informe o caminho do arquivo (ex.: C:\\path\\arquivo.txt)"

        # ========== RAG — URL ESPECÍFICA ==========
        # Se menciona URL/link específico, usa RAG vetorial
        if re.search(r"(?i)(http|www\.|\.com|\.br|link\s+)", msg_lower):
            return rag_url_resposta_vetorial.func(pergunta=mensagem)

        # ========== PESQUISA WEB ==========
        if re.search(r"(?i)(pesquisar|buscar|google|web|internet)", msg_lower):
            # Evita uso indevido para dados internos
            termos_internos = [
                "estoque", "saldo", "pedido", "pedidos", "venda", "vendas",
                "produto", "produtos", "nota fiscal", "nf", "cliente", "fornecedor"
            ]
            if any(t in msg_lower for t in termos_internos):
                pass  # Cai para consulta de negócio
            else:
                return procura_web.func(query=mensagem)

        # ========== CONSULTAS DE NEGÓCIO / BANCO ==========
        termos_negocio = [
            "pedido", "pedidos", "venda", "vendas", "cliente", "clientes",
            "nota fiscal", "nf", "faturamento", "receita",
            "despesa", "comiss[õo]es"
        ]
        # Evita "como..." para DB
        if not re.search(r"(?i)\bcomo\b", msg_lower):
            if any(re.search(t, msg_lower) for t in termos_negocio):
                return consulta_inteligente_prime.func(pergunta=mensagem, slug=real_banco)

        # ========== PERGUNTAS GERAIS/DOCUMENTAÇÃO ==========
        # ❌ REMOVIDO: Chamadas para faiss_context_qa e faiss_condicional_qa
        # ✅ NOVO: Informa que o contexto já foi fornecido
        if "?" in msg_lower or re.search(r"(?i)(como|o\s+que|qual|quais|quando|onde|instru[cç][aã]o|tutorial)", msg_lower):
            return (
                "📎 O contexto relevante já foi fornecido no início da conversa. "
                "Responda com base nesse contexto ou peça esclarecimentos específicos."
            )

        # ========== NENHUMA INTENÇÃO CLARA ==========
        logger.warning("[EXECUTAR_INTENCAO] Nenhuma intenção identificada")
        return (
            "Não identifiquei a intenção. Exemplos:\n"
            "- Cadastro: 'produto <nome> ncm <codigo>'\n"
            "- Saldo: 'saldo do produto <codigo>'\n"
            "- Negócio: 'vendas por cliente no mês'\n"
            "- Pesquisa: 'buscar na web ...'"
        )

    except Exception as e:
        logger.exception("[EXECUTAR_INTENCAO] Erro")
        return f"❌ Erro: {e}"


