import tiktoken
from langchain_core.tools import tool
from ..utils.rag_memory import get_rag_memory, get_tokenizador
from ..configuracoes.config import DEFAULT_TOP_K, DEFAULT_SIMILARITY_THRESHOLD


@tool
def faiss_context_qa(pergunta: str, top_n: int = DEFAULT_TOP_K, limiar_similaridade: float = DEFAULT_SIMILARITY_THRESHOLD, max_chars: int = 1200) -> str:
    """
    Recupera apenas o contexto (chunks) relevantes do FAISS.
    Condições de uso:
    - Use para fornecer contexto auxiliar antes de responder.
    - Não use isoladamente para responder métricas de negócio; combine com DB.
    - Se índice estiver vazio ou nenhum chunk passar o limiar, retorna vazio.
    """
    rag_memory = get_rag_memory()
    if rag_memory.index.ntotal == 0:
        return ""
    query_emb = rag_memory.embed_text(pergunta).reshape(1, -1)
    D, I = rag_memory.index.search(query_emb, top_n)
    chunks = []
    for i, dist in zip(I[0], D[0]):
        if i == -1 or i >= len(rag_memory.meta):
            continue
        similaridade = 1 / (1 + dist)
        if similaridade >= limiar_similaridade:
            chunk = rag_memory.meta[i]
            if isinstance(chunk, str):
                chunks.append(chunk)
            else:
                chunks.append(str(chunk))
    if not chunks:
        return ""
    contexto = "\n\n".join(chunks)
    if len(contexto) > max_chars:
        contexto = contexto[:max_chars]
    return contexto

@tool
def faiss_condicional_qa(pergunta: str, top_n: int = DEFAULT_TOP_K, limiar_similaridade: float = DEFAULT_SIMILARITY_THRESHOLD, mostrar_chunks: bool = False) -> str:
    """
    Busca chunks relevantes no FAISS com base em limiar para QA.
    Condições de uso:
    - Use quando precisar ver/usar os chunks mais próximos para responder.
    - `mostrar_chunks=True` exibe inspeção com similaridade e preview.
    - Não é indicado para perguntas estritamente numéricas de banco.
    """
    rag_memory = get_rag_memory()
    query_emb = rag_memory.embed_text(pergunta).reshape(1, -1)
    if rag_memory.index.ntotal == 0:
        return "Índice FAISS vazio. Use 'rag_url_resposta' ou 'rag_url_resposta_vetorial' para popular o índice."

    D, I = rag_memory.index.search(query_emb, top_n)
    
    chunks_para_qa = []
    chunks_para_mostrar = []

    for i, dist in zip(I[0], D[0]):
        if i == -1 or i >= len(rag_memory.meta):
            continue
        similaridade = 1 / (1 + dist)
        chunk = rag_memory.meta[i]
        tokenizador = get_tokenizador()
        info_chunk = f"Chunk {i}: {chunk[:100]}... Tokens: {len(tokenizador.encode(chunk))} Hash: {hash(chunk)} Similaridade: {similaridade:.2f}"
        
        if similaridade >= limiar_similaridade:
            chunks_para_qa.append(chunk)
        if mostrar_chunks:
            chunks_para_mostrar.append(info_chunk)
    
    resultado = ""
    if mostrar_chunks:
        resultado += "=== Chunks inspecionados ===\n"
        resultado += "\n".join(chunks_para_mostrar)
        resultado += "\n============================\n"
    
    if chunks_para_qa:
        # Limitar tamanho do contexto para evitar respostas muito longas
        contexto_qa = "\n\n".join(chunks_para_qa)
        if len(contexto_qa) > 2000:
            contexto_qa = contexto_qa[:2000] + "..."
        resultado += f"Contexto para QA:\n{contexto_qa}"
    else:
        # Fallback: retornar os top_n mais próximos com similaridade
        candidatos = []
        for i, dist in zip(I[0], D[0]):
            if i == -1 or i >= len(rag_memory.meta):
                continue
            similaridade = 1 / (1 + dist)
            candidatos.append((similaridade, rag_memory.meta[i]))
        candidatos.sort(reverse=True, key=lambda x: x[0])
        if candidatos:
            melhor_sim, melhor_chunk = candidatos[0]
            snippet = melhor_chunk[:400] + ("..." if len(melhor_chunk) > 400 else "")
            resultado += f"Nenhum chunk passou pelo limiar. Melhor candidato (sim={melhor_sim:.2f}):\n{snippet}"
        else:
            resultado += "Nenhum chunk relevante encontrado."
    
    return resultado
