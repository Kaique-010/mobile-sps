import numpy as np
import random
import pandas as pd
import plotly.express as px
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.metrics.pairwise import cosine_similarity
from langchain_core.tools import tool
from ..utils.rag_memory import rag_memory
from openai import OpenAI
from ..configuracoes.config import API_KEY
from ..utils.sqlite_manuais import buscar_manual_por_id

@tool
def plotar_mapa_semantico(pergunta: str = None, metodo: str = "pca", limite: int = 1000) -> str:
    """
    Gera um mapa interativo do cérebro semântico do agente.
    Condições de uso:
    - Use quando o usuário pedir para visualizar ou analisar o "mapa semântico", "distribuição de chunks" ou "cérebro" do agente.
    - Não use para responder perguntas de negócio ou buscar dados; prefira `consulta_inteligente_prime` ou ferramentas de RAG.
    - Parâmetro `metodo`: "pca" ou "tsne".
    """
    if metodo not in {"pca", "tsne"}:
        return "Método inválido. Use 'pca' ou 'tsne'."
    print("[INFO] Gerando mapa semântico com dados do SQLite...")

    # === 1. Extrai embeddings do FAISS ===
    vetores = rag_memory.index.reconstruct_n(0, min(limite, rag_memory.index.ntotal))
    vetores = np.array(vetores)
    metas = rag_memory.meta[:len(vetores)]

    if len(vetores) == 0:
        return "Nenhum vetor encontrado no FAISS."

    # === 2. Redução dimensional ===
    if metodo == "tsne":
        red = TSNE(n_components=2, perplexity=30, random_state=42).fit_transform(vetores)
    else:
        red = PCA(n_components=2).fit_transform(vetores)

    # === 3. Monta dados para DataFrame ===
    fontes, ids, titulos, urls, textos = [], [], [], [], []

    for meta in metas:
        if isinstance(meta, dict):
            id_manual = meta.get("id") or "N/A"
            fonte = meta.get("fonte") or "manual_desconhecido"
            titulo, url = None, None
            try:
                titulo, url = buscar_manual_por_id(id_manual)
            except Exception:
                pass
        else:
            id_manual, fonte, titulo, url = "N/A", "manual_desconhecido", None, None

        fontes.append(fonte)
        ids.append(id_manual)
        titulos.append(titulo or "sem título")
        urls.append(url or "sem URL")
        texto = meta if isinstance(meta, str) else str(meta)
        textos.append(texto[:300] + "..." if len(texto) > 300 else texto)

    df = pd.DataFrame({
        "x": red[:, 0],
        "y": red[:, 1],
        "fonte": fontes,
        "manual_id": ids,
        "titulo": titulos,
        "url": urls,
        "texto": textos
    })

    # === 4. Projeta a pergunta e o chunk mais próximo ===
    if pergunta:
        print(f"[INFO] Projetando a pergunta: {pergunta}")
        client = OpenAI(api_key=API_KEY)
        emb = rag_memory.embed_text(pergunta).reshape(1, -1)

        pca_fit = PCA(n_components=2).fit(vetores)
        emb_red = pca_fit.transform(emb)

        df = pd.concat([
            df,
            pd.DataFrame({
                "x": [emb_red[0, 0]],
                "y": [emb_red[0, 1]],
                "fonte": ["🔴 Pergunta"],
                "manual_id": ["—"],
                "titulo": ["Consulta"],
                "url": ["—"],
                "texto": [pergunta]
            })
        ])

        sim = cosine_similarity(emb, vetores)
        i_prox = int(np.argmax(sim))
        meta_prox = metas[i_prox]
        titulo_prox = titulos[i_prox]
        url_prox = urls[i_prox]

        df = pd.concat([
            df,
            pd.DataFrame({
                "x": [red[i_prox, 0]],
                "y": [red[i_prox, 1]],
                "fonte": ["🟢 Chunk mais próximo"],
                "manual_id": [ids[i_prox]],
                "titulo": [titulo_prox],
                "url": [url_prox],
                "texto": [textos[i_prox]]
            })
        ])

        print(f"[INFO] Chunk mais próximo localizado: {titulo_prox} ({url_prox})")

    # === 5. Cria gráfico interativo ===
    fig = px.scatter(
        df,
        x="x",
        y="y",
        color="fonte",
        hover_data={"manual_id": True, "titulo": True, "url": True, "texto": True},
        title="🧠 Mapa Semântico Interativo — Conexão SQLite",
        width=1100,
        height=750
    )

    fig.update_traces(marker=dict(size=9, opacity=0.85, line=dict(width=0.5, color="white")))
    fig.update_layout(legend_title_text="Origem / Manual")

    # Salva como HTML para abrir no navegador
    fig.write_html("mapa_semantico.html")
    # Evita bloqueio em ambientes sem GUI
    try:
        fig.show()
    except Exception:
        pass

    return "Mapa interativo gerado e salvo em 'mapa_semantico.html'."
