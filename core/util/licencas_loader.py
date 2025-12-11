import os
import logging
from licencas_web.models import LicencaWeb
from django.conf import settings

logger = logging.getLogger(__name__)

def _normalize_doc(doc: str) -> str:
    return str(doc or "").replace(".", "").replace("-", "").replace("/", "").strip()


def carregar_licencas_dict():
    """Carrega licenças da tabela LicencaWeb usando o alias padrão."""
    default_host = os.getenv("DB_HOST", "base.rtalmeida.com.br")
    default_port = os.getenv("DB_PORT", "5432")

    data = []
    conf = getattr(settings, 'DATABASES', {}).get('default', {})
    alias = 'default'
    qs = LicencaWeb.objects.using(alias).all()
    for licenca in qs:
        try:
            norm_doc = _normalize_doc(getattr(licenca, 'cnpj', ''))
            if not (norm_doc.isdigit() and len(norm_doc) == 14):
                continue

            item = {
                "slug": getattr(licenca, 'slug', ''),
                "cnpj": norm_doc,
                "db_name": getattr(licenca, 'db_name', '') or getattr(licenca, 'slug', ''),
                "db_host": getattr(licenca, 'db_host', '') or default_host,
                "db_port": getattr(licenca, 'db_port', '') or default_port,
                "db_user": getattr(licenca, 'db_user', '') or None,
                "db_password": getattr(licenca, 'db_password', '') or None,
            }

            # Armazena modulos se disponíveis (string JSON ou lista)
            mods = getattr(licenca, 'modulos', '[]')
            item["modulos"] = mods

            data.append(item)
        except Exception:
            continue
    return data
