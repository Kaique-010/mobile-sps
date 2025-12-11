import os
from pathlib import Path
import re
from decouple import config
from django.conf import settings
from django.db import connections
from core.licenca_context import get_current_request
from core.middleware import get_licenca_slug 
from core.licenca_context import get_licencas_map

json_path = Path(__file__).resolve().parent / 'licencas.json'





def limpar_cnpj(cnpj):
    return re.sub(r'\D', '', cnpj)

def get_licenca_db_config(request):
    path_parts = request.path.strip('/').split('/')
    slug = path_parts[1] if len(path_parts) > 1 else None  # /api/<slug>/...

    if not slug:
        return "default"  # Ou lança erro, se quiser

    licenca = next((lic for lic in get_licencas_map() if lic["slug"] == slug), None)
    if not licenca:
        raise Exception(f"Licença com slug '{slug}' não encontrada.")

    if slug in settings.DATABASES:
        return slug

    prefixo = slug.upper()
    db_user = licenca.get("db_user") or config(f"{prefixo}_DB_USER", default=None)
    db_password = licenca.get("db_password") or config(f"{prefixo}_DB_PASSWORD", default=None)
    if not db_user or not db_password:
        raise Exception(f"Credenciais não encontradas para {slug}")

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
    licenca = next((x for x in get_licencas_map() if x['cnpj'] == docu), None)
    return licenca.get('modulos', []) if licenca else []
