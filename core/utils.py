# utils.py
from decouple import config
from django.db import connections
from core import settings
from core.licenca_context import LICENCAS_MAP


def get_db_from_slug(slug):
    if not slug:
        return "default"

    licenca = next((lic for lic in LICENCAS_MAP if lic["slug"] == slug), None)
    if not licenca:
        raise Exception(f"Licença com slug '{slug}' não encontrada.")

    if slug in settings.DATABASES:
        return slug

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

def get_licenca_db_config(request):
    path_parts = request.path.strip('/').split('/')
    slug = path_parts[1] if len(path_parts) > 1 else None
    return get_db_from_slug(slug)
