import hashlib
from django.conf import settings

def gerar_hash_str(empr, codi):
    """Gera o hash raw a partir de empresa e código, centralizando a lógica"""
    # Garantir que sejam strings limpas
    s_empr = str(empr).strip()
    s_codi = str(codi).strip()
    # Usar settings.SECRET_KEY em vez de os.getenv para consistência com Django
    raw = f"{s_empr}:{s_codi}:{settings.SECRET_KEY}"
    return hashlib.sha1(raw.encode()).hexdigest()[:12]
