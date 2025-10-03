import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Configurações da API
API_KEY = os.environ.get("OPENAI_API_KEY")
EMBED_DIM = 1536  # text-embedding-3-small

# Caminhos dos arquivos (absolutos, relativos ao pacote Assistente_Spart)
BASE_DIR = Path(__file__).resolve().parent.parent
CAMINHO_FAISS = str(BASE_DIR / "faiss" / "faiss_full_rag.index")
CAMINHO_META = str(BASE_DIR / "faiss" / "faiss_full_rag_meta.pkl")
DATASET_PATH = str(BASE_DIR / "dataset_finetuning.jsonl")
DB_PATH = str(BASE_DIR / "db" / "manuais.db")

# Configurações do modelo
EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o"
TOKENIZER_ENCODING = "cl100k_base"

# Configurações de chunking
MAX_TOKENS_PER_CHUNK = 500
DEFAULT_TOP_K = 2
DEFAULT_SIMILARITY_THRESHOLD = 0.55  # Ajustado para reduzir contexto e acelerar QA