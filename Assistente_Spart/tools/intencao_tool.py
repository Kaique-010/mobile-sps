from langchain_core.tools import tool
import re
import logging
from core.utils import get_db_from_slug

# Tools de negócio
from .db_tool import (
    cadastrar_produtos,
    consultar_saldo,
    consultar_titulos_a_pagar,
    consultar_titulos_a_receber,
    consulta_inteligente_prime,
    historico_de_pedidos_cliente,
    historico_de_pedidos,
)
from .rag_tool import rag_url_resposta_vetorial
from .web_tool import procura_web
from .file_tool import ler_documentos
from .tool_mapa_semantico import plotar_mapa_semantico
from .fiscal import fiscal_router

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
    - Fiscal: "nota fiscal|emissão|devolução|CFOP|CST|impostos|rejeições SEFAZ|erro fiscal" -> fiscal_router
    
    - Histórico de pedidos do cliente: "meu histórico de pedidos" -> historico_de_pedidos_cliente
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
        


        def mes_pt_para_num(m):
            mapa = {
                'janeiro':1,'fevereiro':2,'marco':3,'março':3,'abril':4,'maio':5,
                'junho':6,'julho':7,'agosto':8,'setembro':9,'outubro':10,'novembro':11,'dezembro':12
            }
            return mapa.get(m.strip().lower())

        def normalizar_data_token(dia:str, mes_nome:str, ano:str=None):
            try:
                d = int(dia)
                m = mes_pt_para_num(mes_nome) if mes_nome else None
                y = int(ano) if ano else __import__('datetime').datetime.now().year
                if not m:
                    m = __import__('datetime').datetime.now().month
                return f"{y:04d}-{m:02d}-{d:02d}"
            except Exception:
                return None

        def extrair_periodo(texto:str):
            import re
            r1 = re.search(r"(?i)(?:de|desde)\s*(\d{1,2})(?:\s*de\s*([a-zçãõáéíóú]+))?\s*(?:de\s*(\d{4}))?\s*(?:at[eé]|a)\s*(\d{1,2})(?:\s*de\s*([a-zçãõáéíóú]+))?\s*(?:de\s*(\d{4}))?", texto)
            if r1:
                di, mi, yi, df, mf, yf = r1.groups()
                d_ini = normalizar_data_token(di, mi, yi)
                d_fim = normalizar_data_token(df, mf, yf)
                return d_ini, d_fim
            r2 = re.search(r"(?i)(\d{1,2})[/-](\d{1,2})[/-](\d{2,4}).*?(?:at[eé]|a)\s*(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", texto)
            if r2:
                d1,m1,y1,d2,m2,y2 = r2.groups()
                y1 = int(y1); y1 = 2000+y1 if y1<100 else y1
                y2 = int(y2); y2 = 2000+y2 if y2<100 else y2
                return f"{y1:04d}-{int(m1):02d}-{int(d1):02d}", f"{y2:04d}-{int(m2):02d}-{int(d2):02d}"
            return None, None

        def extrair_cliente(texto:str):
            import re
            m_cod = re.search(r"(?i)cliente\s*(\d{1,9})", texto)
            if m_cod:
                return m_cod.group(1), None
            m_nome = re.search(r"(?i)(?:do\s+cliente|cliente)\s+([A-Za-zÁ-Úá-úÇãõêéôíú\s']{3,})", texto)
            if m_nome:
                return None, m_nome.group(1).strip()
            return None, None

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

        # ========== HISTÓRICO DE PEDIDOS ==========
        if re.search(r"(?i)(hist[óo]rico\s+de\s+pedidos|hist[óo]rico\s+geral\s+de\s+pedidos|relat[óo]rio\s+de\s+pedidos|pedidos\s+por\s+cliente)", msg_lower):
            di, df = extrair_periodo(mensagem)
            cod, nome = extrair_cliente(mensagem)
            if cod or nome:
                return historico_de_pedidos_cliente.func(
                    banco=real_banco,
                    empresa_id=str(empresa_id),
                    filial_id=str(filial_id),
                    data_inicial=di,
                    data_final=df,
                    codigo_cliente=cod,
                    nome_cliente=nome,
                )
            else:
                return historico_de_pedidos.func(
                    banco=real_banco,
                    empresa_id=str(empresa_id),
                    filial_id=str(filial_id),
                    data_inicial=di,
                    data_final=df,
                )

        # Substitua as seções de títulos no executar_intencao:

        # ========== CONSULTA DE TITULOS A PAGAR ==========
        if re.search(r"(?i)(t[ií]tulo|titulo).*?(pagar|a\s+pagar|contas\s+a\s+pagar)", msg_lower):
            logger.info(f"[EXECUTAR_INTENCAO] Consulta títulos a pagar")
            try:
                resultado = consultar_titulos_a_pagar.func(
                    banco=real_banco,
                    empresa_id=str(empresa_id),
                    filial_id=str(filial_id),
                )
                # Garante que retorna string
                return str(resultado) if resultado else "Sem dados de títulos a pagar."
            except Exception as e:
                logger.error(f"[TITULOS_PAGAR] Erro: {e}")
                return f"❌ Erro ao consultar títulos a pagar: {str(e)}"

        # ========== CONSULTA DE TITULOS A RECEBER ==========
        if re.search(r"(?i)(t[ií]tulo|titulo).*?(receber|a\s+receber|contas\s+a\s+receber)", msg_lower):
            logger.info(f"[EXECUTAR_INTENCAO] Consulta títulos a receber")
            try:
                resultado = consultar_titulos_a_receber.func(
                    banco=real_banco,
                    empresa_id=str(empresa_id),
                    filial_id=str(filial_id),
                )
                # Garante que retorna string
                return str(resultado) if resultado else "Sem dados de títulos a receber."
            except Exception as e:
                logger.error(f"[TITULOS_RECEBER] Erro: {e}")
                return f"❌ Erro ao consultar títulos a receber: {str(e)}"
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
                if re.search(r"(?i)hist[óo]rico|relat[óo]rio\s+de\s+pedidos|pedidos\s+por\s+cliente", msg_lower):
                    pass
                else:
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


