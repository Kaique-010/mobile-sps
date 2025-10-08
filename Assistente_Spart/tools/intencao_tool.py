from langchain_core.tools import tool
import re
import logging
from collections import Counter
from statistics import mean
from core.utils import get_db_from_slug

# Tools de negócio e conhecimento
from .db_tool import (
    cadastrar_produtos,
    consultar_saldo,
    consulta_inteligente_prime,
)
from .qa_tools import faiss_context_qa, faiss_condicional_qa
from .rag_tool import rag_url_resposta_vetorial
from .web_tool import procura_web
from .file_tool import ler_documentos
from .tool_mapa_semantico import plotar_mapa_semantico

logger = logging.getLogger(__name__)

@tool
def identificar_intencao(mensagem: str) -> dict:
    """
    Identifica a intenção do Usuário (cadastrar produto ou consultar saldo).
    Extrai parâmetros relevantes da frase: nome, código, empresa, filial.
    """
    msg_lower = mensagem.lower()

    # Defaults
    empresa = "1"
    filial = "1"

    # Captura empresa
    empresa_match = re.search(r"empresa\s+(\d+)", msg_lower)
    if empresa_match:
        empresa = empresa_match.group(1)

    # Captura filial
    filial_match = re.search(r"filial\s+(\d+)", msg_lower)
    if filial_match:
        filial = filial_match.group(1)

    # Cadastro
    if "cadastro" in msg_lower or "cadastrar" in msg_lower or "novo produto" in msg_lower:
        nome = re.search(r"produto\s+(.+?)(?=\s+código|\s+preço|$)", msg_lower)
        codigo = re.search(r"código\s+(\d+)", msg_lower)

        return {
            "acao": "cadastrar_produto",
            "nome": nome.group(1).strip() if nome else None,
            "codigo": codigo.group(1) if codigo else None,
            "empresa": empresa,
            "filial": filial
        }

    # Consulta de saldo
    elif "saldo" in msg_lower or "quantidade" in msg_lower or "estoque" in msg_lower:
        codigo_match = re.search(r"produto\s+(\d+)", msg_lower)
        return {
            "acao": "consultar_saldo",
            "codigo": codigo_match.group(1) if codigo_match else None,
            "empresa": empresa,
            "filial": filial
        }
    elif "?" in msg_lower:
        return {"acao": "pergunta", "empresa": empresa, "filial": filial}

    return {"acao": "desconhecida", "empresa": empresa, "filial": filial}


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

    Regras principais:
    - Cadastro: "produto <nome> ncm <codigo>" -> cadastrar_produtos
    - Saldo: contém "saldo|estoque|quantidade" e "codigo|produto <número>" -> consultar_saldo
    - Pergunta de negócio (vendas, pedidos, clientes, etc.) -> consulta_inteligente_prime
    - Pergunta geral/documentação/manual -> faiss_context_qa ou rag_url_resposta_vetorial
    - Pesquisa na web (google, web, internet) -> procura_web
    - Leitura de arquivo local (caminho/arquivo) -> ler_documentos
    - Visualização do cérebro semântico (mapa semântico, pca/tsne) -> plotar_mapa_semantico

    Roteamento de banco:
      1. banco (explicitamente passado)
      2. slug (convertido via get_db_from_slug)
      3. 'default' (fallback)
    """
    try:
        # ==========================================================
        # Determina o banco correto com fallback seguro
        # ==========================================================
        if banco and banco != "default":
            real_banco = banco
        elif slug:
            real_banco = get_db_from_slug(slug)
        else:
            real_banco = "default"

        logger.info(f"[EXECUTAR_INTENCAO] Usando banco: {real_banco} | Empresa: {empresa_id} | Filial: {filial_id}")
        msg_lower = mensagem.lower()

        # ==========================================================
        # PERGUNTA DE MODO/INSTRUÇÃO ("como cadastrar", etc.)
        # ==========================================================
        if re.search(r"(?i)como(\s+posso|\s+fa[cç]o)?\s+cadastrar", msg_lower):
            return (
                "Para cadastrar produto, envie no formato: 'produto <nome> ncm <codigo>'.\n"
                "Exemplo: produto Mesa de Jantar ncm 94036000"
            )

        # ==========================================================
        # CADASTRO DE PRODUTO
        # ==========================================================
        m_cad = re.search(r"(?i)produto\s+(.+?)\s+ncm\s+(\d+)", mensagem)
        if m_cad:
            nome = m_cad.group(1).strip()
            ncm = m_cad.group(2).strip()
            logger.info(f"[EXECUTAR_INTENCAO] Cadastro detectado: produto={nome}, ncm={ncm}")

            return cadastrar_produtos.func(
                prod_nome=nome,
                prod_ncm=ncm,
                banco=real_banco,
                empresa_id=str(empresa_id),
                filial_id=str(filial_id),
            )
        # Se pediu cadastro mas sem NCM, orienta formato
        if re.search(r"(?i)cadastro|cadastrar|novo\s+produto", msg_lower) and not m_cad:
            return (
                "Para efetivar o cadastro, informe também o NCM: 'produto <nome> ncm <codigo>'.\n"
                "Exemplo: produto Mesa de Jantar ncm 94036000"
            )

        # ==========================================================
        # CONSULTA DE SALDO
        # ==========================================================
        m_saldo_kw = re.search(r"(?i)(saldo|estoque|quantidade)", msg_lower)
        m_saldo_cod = re.search(r"(?i)(c[oó]digo|produto)\s+(\d+)", msg_lower)
        if m_saldo_kw and m_saldo_cod:
            codigo = m_saldo_cod.group(2).strip()
            logger.info(f"[EXECUTAR_INTENCAO] Consulta de saldo detectada: produto_codigo={codigo}")

            return consultar_saldo.func(
                produto_codigo=codigo,
                banco=real_banco,
                empresa_id=str(empresa_id),
                filial_id=str(filial_id),
            )

        # ==========================================================
        # VISUALIZAÇÃO — MAPA SEMÂNTICO
        # ==========================================================
        if re.search(r"(?i)(mapa\s+sem[aâ]ntico|c[ée]rebro|pca|tsne)", msg_lower):
            metodo = "tsne" if "tsne" in msg_lower else "pca"
            return plotar_mapa_semantico.func(pergunta=mensagem, metodo=metodo)

        # ==========================================================
        # LEITURA DE DOCUMENTO LOCAL
        # ==========================================================
        if re.search(r"(?i)(ler|abrir)\s+(arquivo|documento)", msg_lower):
            # Tenta extrair um caminho entre aspas ou após 'arquivo'
            m_path = re.search(r"(?i)arquivo\s+([\w:\\\/\.\-]+)|['\"]([^'\"]+)['\"]", mensagem)
            file_path = None
            if m_path:
                file_path = m_path.group(1) or m_path.group(2)
            if file_path:
                return ler_documentos.func(file_path=file_path)
            else:
                return "Informe o caminho do arquivo para leitura (ex.: C:\\path\\arquivo.txt)."

        # ==========================================================
        # RAG — MANUAIS / DOCUMENTAÇÃO
        # ==========================================================
        if re.search(r"(?i)(manual|documenta[cç][aã]o|kb|artigo|link|url)", msg_lower):
            return rag_url_resposta_vetorial.func(pergunta=mensagem)

        # ==========================================================
        # PESQUISA NA WEB
        # ==========================================================
        if re.search(r"(?i)(pesquisar|buscar|google|web|internet)", msg_lower):
            # Evita uso indevido para dados internos
            termos_internos = [
                "estoque", "saldo", "pedido", "pedidos", "venda", "vendas",
                "produto", "produtos", "nota fiscal", "nf", "cliente", "fornecedor"
            ]
            if any(t in msg_lower for t in termos_internos):
                # Cai para consulta de negócio
                pass
            else:
                return procura_web.func(query=mensagem)

        # ==========================================================
        # CONSULTAS DE NEGÓCIO / BANCO
        # ==========================================================
        termos_negocio = [
            "pedido", "pedidos", "venda", "vendas", "cliente", "clientes",
            "nota fiscal", "nf", "faturamento", "receita",
            "despesa", "comiss[õo]es", "saldo", "estoque"
        ]
        # Evita rotear "como ..." para DB
        if re.search(r"(?i)\bcomo\b", msg_lower):
            termos_negocio = []
        if any(re.search(t, msg_lower) for t in termos_negocio):
            return consulta_inteligente_prime.func(pergunta=mensagem, slug=real_banco)

        # ==========================================================
        # PERGUNTA GERAL — CONTEXTO FAISS
        # ==========================================================
        if "?" in msg_lower or re.search(r"(?i)(como|o\s+que|qual|quais|quando|onde|instru[cç][aã]o|tutorial)", msg_lower):
            # Usa FAISS condicional para perguntas gerais
            return faiss_condicional_qa.func(pergunta=mensagem)

        # ==========================================================
        # NENHUMA INTENÇÃO CLARA
        # ==========================================================
        logger.warning("[EXECUTAR_INTENCAO] Nenhuma intenção clara identificada.")
        return (
            "Não identifiquei claramente a intenção. Exemplos: \n"
            "- Cadastro de produto: 'produto <nome> ncm <codigo>'\n"
            "- Saldo de estoque: 'saldo do produto <codigo>'\n"
            "- Pergunta de negócio: 'vendas por cliente no mês'\n"
            "- Documentação/manual: 'como configurar X (link/url)'\n"
            "- Pesquisa geral: 'buscar na web ...'\n"
            "- Visualizar mapa semântico: 'plotar mapa pca'"
        )

    except Exception as e:
        logger.exception("[EXECUTAR_INTENCAO] Erro inesperado")
        return f"❌ Erro ao executar intenção: {e}"