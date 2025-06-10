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





def limpar_cnpj(cnpj):
    return re.sub(r'\D', '', cnpj)

def get_licenca_db_config(request):
    path_parts = request.path.strip('/').split('/')
    slug = path_parts[1] if len(path_parts) > 1 else None  # /api/<slug>/...

    if not slug:
        return "default"  # Ou lança erro, se quiser

    licenca = next((lic for lic in LICENCAS_MAP if lic["slug"] == slug), None)
    if not licenca:
        raise Exception(f"Licença com slug '{slug}' não encontrada.")

    if slug in settings.DATABASES:
        return slug

    # Carrega credenciais do .env
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


def get_modulos_por_docu(docu):
    from core.registry import LICENCAS_MAP
    licenca = next((x for x in LICENCAS_MAP if x['cnpj'] == docu), None)
    return licenca.get('modulos', []) if licenca else []