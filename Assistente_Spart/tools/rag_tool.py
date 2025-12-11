import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from ..utils.rag_memory import get_rag_memory
from ..utils.sqlite_manuais import buscar_manual_por_pergunta_vetorial, inserir_manual_com_embedding
from ..configuracoes.config import DEFAULT_TOP_K

@tool
def rag_url_resposta_vetorial(pergunta: str, url: str = None, k: int = DEFAULT_TOP_K) -> str:
    """
    Responde com RAG usando FAISS e SQLite (manuais).
    Condições de uso:
    - Use quando a pergunta indicar necessidade de "manual", "documentação",
      "como fazer", ou referência a um "link/URL".
    - Evite usar para métricas de negócio (pedidos, vendas, estoque);
      prefira `consulta_inteligente_prime`.
    - Se `url` for fornecido, indexa e usa esse conteúdo; caso contrário,
      seleciona manual mais relevante do banco vetorial.
    """
    if not pergunta or len(pergunta.strip()) < 8:
        return "Pergunta muito curta para RAG. Seja mais específico."
    # 1) Tenta responder diretamente do FAISS (rápido)
    try:
        rag_memory = get_rag_memory()
        contexto = "\n\n".join(rag_memory.query(pergunta, k=k))
        if contexto.strip():
            return contexto
    except Exception:
        pass

    # 2) Seleciona manual mais relevante no SQLite (barato)
    manuais_relevantes = buscar_manual_por_pergunta_vetorial(pergunta)
    if manuais_relevantes:
        sim, id_, titulo, url_manual = manuais_relevantes[0]
        print(f"[INFO] Usando manual mais relevante (sim={sim:.2f}): {titulo}")
        url = url_manual
    elif not url:
        return "Nenhum manual relevante encontrado. Informe um URL."
    else:
        inserir_manual_com_embedding(titulo=url.split("/")[-1], url=url)

    # 3) Faz scraping apenas se necessário (timeout menor)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
    except Exception as e:
        return f"Erro ao acessar URL: {e}"

    soup = BeautifulSoup(r.text, "html.parser")
    artigo = (soup.select_one("div.col-sm-9.kb-article-view-content article#kb-article")
              or soup.select_one("article#kb-article")
              or soup.find("article"))
    if not artigo:
        return "Não encontrei o artigo na página."

    # 4) Indexa conteúdo no FAISS (só adiciona chunks novos)
    texto = artigo.get_text(separator="\n", strip=True)
    rag_memory = get_rag_memory()
    chunks = rag_memory.chunk_text(texto)
    rag_memory.add_texts(chunks)

    # 5) Responde usando o índice
    contexto = "\n\n".join(rag_memory.query(pergunta, k=k))
    return contexto


