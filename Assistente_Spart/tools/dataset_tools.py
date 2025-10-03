import json
import tiktoken
from langchain_core.tools import tool
from ..configuracoes.config import API_KEY, DATASET_PATH, TOKENIZER_ENCODING
from openai import OpenAI

client = OpenAI(api_key=API_KEY)
tokenizador = tiktoken.get_encoding(TOKENIZER_ENCODING)


@tool
def salvar_dataset_finetuning(pergunta: str, resposta: str, chunks_contexto: str, url_origem: str = None) -> str:
    """Salva pares pergunta-resposta com contexto para dataset de fine-tuning"""
    registro = {
        "pergunta": pergunta,
        "contexto": chunks_contexto,
        "resposta": resposta,
        "url_origem": url_origem,
        "num_tokens_contexto": len(tokenizador.encode(chunks_contexto)),
        "hash_contexto": hash(chunks_contexto)
    }

    with open(DATASET_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")

    return f"Par salvo para fine-tuning: pergunta='{pergunta[:50]}...', tokens={registro['num_tokens_contexto']}"
