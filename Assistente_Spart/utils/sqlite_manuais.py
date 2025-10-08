import sqlite3
import os
import numpy as np
from openai import OpenAI
from ..configuracoes.config import API_KEY, DB_PATH, EMBEDDING_MODEL

# Garante diretório do banco
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

client = OpenAI(api_key=API_KEY)

# Cria tabela (robusto em multi-thread)
with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS manuais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            embedding BLOB
        )
    """
    )
    conn.commit()

def gerar_embedding(texto: str):
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=texto)
    return np.array(resp.data[0].embedding, dtype="float32")

def inserir_manual_com_embedding(titulo: str, url: str):
    embedding = gerar_embedding(titulo)
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        c = conn.cursor()
        # UPSERT por URL: se existir, atualiza título e embedding
        c.execute(
            """
            INSERT INTO manuais (titulo, url, embedding)
            VALUES (?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                titulo=excluded.titulo,
                embedding=excluded.embedding
            """,
            (titulo, url, embedding.tobytes())
        )
        conn.commit()

def buscar_manual_por_pergunta_vetorial(pergunta: str, top_n: int = 3):
    query_emb = gerar_embedding(pergunta)
    qnorm = np.linalg.norm(query_emb)
    if qnorm == 0:
        return []
    resultados = []

    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute("SELECT id, titulo, url, embedding FROM manuais")
        rows = c.fetchall()
        for id_, titulo, url, emb_blob in rows:
            emb = np.frombuffer(emb_blob, dtype="float32")
            # ignora embeddings com dimensão incompatível
            if emb.size != query_emb.size:
                continue
            denom = (qnorm * np.linalg.norm(emb))
            if denom == 0:
                continue
            sim = float(np.dot(query_emb, emb) / denom)
            resultados.append((sim, id_, titulo, url))

    resultados.sort(reverse=True, key=lambda x: x[0])
    return resultados[:top_n]

def buscar_manual_por_id(id_: int):
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute("SELECT id, titulo, url, embedding FROM manuais WHERE id = ?", (id_,))
        row = c.fetchone()
        if row:
            id_, titulo, url, emb_blob = row
            emb = np.frombuffer(emb_blob, dtype="float32")
            return {"id": id_, "titulo": titulo, "url": url, "embedding": emb}
        return None