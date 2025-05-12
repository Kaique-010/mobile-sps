import json
import os
from pathlib import Path
import re
from decouple import config
from django.conf import settings
from django.db import connections
from core.licenca_context import get_current_request
from core.middleware import get_licenca_slug 

# Carrega o arquivo licencas.json
json_path = Path(__file__).resolve().parent / 'licencas.json'
LICENCAS_MAP = json.load(open(json_path))
print(f"Licenças carregadas: {LICENCAS_MAP}")




def limpar_cnpj(cnpj):
    return re.sub(r'\D', '', cnpj)

def get_licenca_db_config():
    slug = get_licenca_slug() 
    if not slug:
        return "default"  # Se não tiver slug, usar o banco padrão

    licenca = next((lic for lic in LICENCAS_MAP if lic["slug"] == slug), None)
    if not licenca:
        raise Exception(f"Licença com slug '{slug}' não encontrada.")

    # Se o slug estiver no banco de dados de configurações, usamos o banco de dados correspondente
    if slug in settings.DATABASES:
        return slug

    # Caso contrário, configura o banco de dados para a licença com base nas configurações
    prefixo = slug.upper()
    db_user = config(f"{prefixo}_DB_USER")
    db_password = config(f"{prefixo}_DB_PASSWORD")

    settings.DATABASES[slug] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': licenca["db_name"],
        'USER': db_user,
        'PASSWORD': db_password,
        'HOST': licenca["db_host"],
        'PORT': licenca["db_port"],
    }

    connections.ensure_defaults(slug)
    connections.prepare_test_settings(slug)

    return slug