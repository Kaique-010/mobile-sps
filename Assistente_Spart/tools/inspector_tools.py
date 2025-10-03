import tiktoken
import requests
from langchain_core.tools import tool
from openai import OpenAI
from bs4 import BeautifulSoup
from ..utils.sqlite_manuais import inserir_manual_com_embedding
from ..utils.rag_memory import rag_memory
from ..configuracoes.config import API_KEY, TOKENIZER_ENCODING, DEFAULT_TOP_K

client = OpenAI(api_key=API_KEY)
tokenizador = tiktoken.get_encoding(TOKENIZER_ENCODING)


@tool
def rag_url_resposta(url: str, pergunta: str, k: int = DEFAULT_TOP_K) -> str:
    """Extrai conteúdo de uma URL e responde perguntas usando RAG"""
    # 0) Tenta responder diretamente do FAISS
    try:
        contexto = "\n\n".join(rag_memory.query(pergunta, k=k))
        if contexto.strip():
            return contexto
    except Exception:
        pass

    # 1) Inserir manual no banco se não existir
    try:
        inserir_manual_com_embedding(titulo=url.split("/")[-1], url=url)
    except Exception as e:
        print(f"Aviso: {e}")

    # 2) Scraping apenas se necessário (timeout menor)
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

    texto = artigo.get_text(separator="\n", strip=True)
    chunks = rag_memory.chunk_text(texto)
    rag_memory.add_texts(chunks)

    contexto = "\n\n".join(rag_memory.query(pergunta, k=k))
    return contexto


@tool
def inspector_faiss(pergunta: str, top_n: int = 5) -> str:
    """Inspeciona o índice FAISS e retorna informações sobre chunks relevantes"""
    if rag_memory.index.ntotal == 0:
        return "Índice FAISS vazio. Adicione documentos primeiro."
    
    query_emb = rag_memory.embed_text(pergunta).reshape(1, -1)
    D, I = rag_memory.index.search(query_emb, min(top_n, rag_memory.index.ntotal))
    
    resultado = f"=== Inspeção FAISS ===\n"
    resultado += f"Total de chunks no índice: {rag_memory.index.ntotal}\n"
    resultado += f"Top {len(I[0])} chunks mais relevantes:\n\n"
    
    tokenizador = tiktoken.get_encoding("cl100k_base")
    
    for i, (idx, dist) in enumerate(zip(I[0], D[0])):
        if idx < len(rag_memory.meta):
            chunk = rag_memory.meta[idx]
            similaridade = 1 / (1 + dist)
            tokens = len(tokenizador.encode(chunk))
            resultado += f"{i+1}. Chunk {idx}:\n"
            resultado += f"   Similaridade: {similaridade:.3f}\n"
            resultado += f"   Tokens: {tokens}\n"
            resultado += f"   Preview: {chunk[:150]}...\n\n"
    
    return resultado
