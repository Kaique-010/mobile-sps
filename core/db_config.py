from decouple import config
from core.licenca_checker import get_db_name_by_docu
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

def get_license_database():
    return {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(BASE_DIR / 'db.sqlite3'),  # Banco SQLite que mantém a licença
    }

def get_dynamic_db_config(docu: str) -> dict:
    lice_nome = get_db_name_by_docu(docu)
    if not lice_nome:
        raise ValueError("CNPJ não autorizado.")
    
    db_config = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config(f'{lice_nome}_DB_NAME', default=lice_nome),
        'USER': config(f'{lice_nome}_DB_USER'),
        'PASSWORD': config(f'{lice_nome}_DB_PASSWORD'),
        'HOST': config(f'{lice_nome}_DB_HOST'),
        'PORT': config(f'{lice_nome}_DB_PORT', default='5432'),
    }

    # Verificação se as variáveis de ambiente estão presentes
    for key, value in db_config.items():
        if not value:
            raise ValueError(f"Variável de ambiente '{key}' não encontrada para o banco {lice_nome}.")
    
    return db_config