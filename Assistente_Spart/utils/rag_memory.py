import os, pickle, numpy as np
import faiss
import tiktoken
from openai import OpenAI
from ..configuracoes.config import API_KEY, CAMINHO_FAISS, CAMINHO_META, EMBED_DIM, EMBEDDING_MODEL, TOKENIZER_ENCODING, MAX_TOKENS_PER_CHUNK

client = OpenAI(api_key=API_KEY)
tokenizador = tiktoken.get_encoding(TOKENIZER_ENCODING)

class RAGMemory:
    def __init__(self, embed_dim=EMBED_DIM):
        self.embed_dim = embed_dim
        if os.path.exists(CAMINHO_FAISS):
            try:
                idx = faiss.read_index(CAMINHO_FAISS)
                if idx.d != embed_dim:
                    # dimensão incompatível: reinicia índice e reconstroi a partir do meta existente
                    self.index = faiss.IndexFlatL2(embed_dim)
                    try:
                        with open(CAMINHO_META, "rb") as f:
                            self.meta = pickle.load(f)
                    except Exception:
                        self.meta = []
                    if self.meta:
                        self._rebuild_from_meta()
                else:
                    self.index = idx
                    with open(CAMINHO_META, "rb") as f:
                        self.meta = pickle.load(f)
            except Exception:
                self.index = faiss.IndexFlatL2(embed_dim)
                self.meta = []
        else:
            self.index = faiss.IndexFlatL2(embed_dim)
            self.meta = []
        self.ids_set = set(hash(text) for text in self.meta)

    def embed_text(self, texto: str):
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=texto)
        return np.array(resp.data[0].embedding, dtype="float32")

    def chunk_text(self, texto: str, max_tokens=MAX_TOKENS_PER_CHUNK):
        tokens = tokenizador.encode(texto)
        chunks = []
        for i in range(0, len(tokens), max_tokens):
            chunk_tokens = tokens[i:i+max_tokens]
            chunks.append(tokenizador.decode(chunk_tokens))
        return chunks

    def add_texts(self, textos: list[str]):
        novos_chunks = []
        for t in textos:
            h = hash(t)
            if h not in self.ids_set:
                novos_chunks.append(t)
                self.ids_set.add(h)
        if novos_chunks:
            # Embeddings em batch para reduzir latência
            resp = client.embeddings.create(model=EMBEDDING_MODEL, input=novos_chunks)
            embeddings = [np.array(item.embedding, dtype="float32") for item in resp.data]
            self.index.add(np.array(embeddings))
            self.meta.extend(novos_chunks)
            self._persist()

    def _persist(self):
        os.makedirs(os.path.dirname(CAMINHO_FAISS), exist_ok=True)
        faiss.write_index(self.index, CAMINHO_FAISS)
        with open(CAMINHO_META, "wb") as f:
            pickle.dump(self.meta, f)

    def _rebuild_from_meta(self):
        # Re-embeddings em batch e reconstrução do índice
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=self.meta)
        embeddings = [np.array(item.embedding, dtype="float32") for item in resp.data]
        self.index.reset()
        self.index.add(np.array(embeddings))
        self._persist()

    def query(self, pergunta: str, k: int = 3):
        if self.index.ntotal == 0:
            return []
        query_emb = self.embed_text(pergunta).reshape(1, -1)
        D, I = self.index.search(query_emb, k)
        resultados = []
        for i in I[0]:
            if i == -1:
                continue
            if 0 <= i < len(self.meta):
                resultados.append(self.meta[i])
        return resultados

rag_memory = RAGMemory()
