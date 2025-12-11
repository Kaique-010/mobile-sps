import os
import logging
import json
from pathlib import Path
from decouple import config
from django.conf import settings
from django.db import connections

logger = logging.getLogger(__name__)

def _normalize_doc(doc: str) -> str:
    return str(doc or "").replace(".", "").replace("-", "").replace("/", "").strip()

def carregar_licencas_dict():
    default_host = os.getenv("DB_HOST", "base.rtalmeida.com.br")
    default_port = os.getenv("DB_PORT", "5432")

    conf = getattr(settings, 'DATABASES', {}).get('default', {})
    alias = 'default'
    logger.warning("[LICENCAS_LOADER] alias=%s db=%s@%s", alias, conf.get('NAME'), conf.get('HOST'))

    _bootstrap_licencas_web_if_missing()

    data = []
    try:
        with connections[alias].cursor() as cur:
            cur.execute("SELECT slug, cnpj, db_name, db_host, db_port, modulos, db_user, db_password FROM licencas_web ORDER BY slug")
            rows = cur.fetchall()
            for row in rows:
                slug, cnpj, db_name, db_host, db_port, modulos, db_user, db_password = row
                norm_doc = _normalize_doc(cnpj or '')
                if not (norm_doc.isdigit() and len(norm_doc) == 14):
                    continue
                item = {
                    "slug": slug or '',
                    "cnpj": norm_doc,
                    "db_name": db_name or (slug or ''),
                    "db_host": db_host or default_host,
                    "db_port": db_port or default_port,
                    "db_user": db_user or None,
                    "db_password": db_password or None,
                    "modulos": modulos or '[]',
                }
                data.append(item)
    except Exception as e:
        logger.warning("[LICENCAS_LOADER] leitura falhou: %s", e)
        data = []

    logger.warning("[LICENCAS_LOADER] count=%s", len(data))
    return data

def _bootstrap_licencas_web_if_missing():
    try:
        conn = connections['default']
        tables = conn.introspection.table_names()
        if 'licencas_web' in tables:
            return
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE licencas_web (
                    id SERIAL PRIMARY KEY,
                    slug VARCHAR(64) UNIQUE NOT NULL,
                    cnpj VARCHAR(20) NOT NULL,
                    db_name VARCHAR(100) NOT NULL,
                    db_host VARCHAR(200) NOT NULL,
                    db_port VARCHAR(10) NOT NULL,
                    modulos TEXT NOT NULL DEFAULT '[]',
                    db_user VARCHAR(128) DEFAULT '',
                    db_password VARCHAR(256) DEFAULT ''
                )
                """
            )
            p = Path(__file__).resolve().parents[0] / 'licencas.json'
            if not p.exists():
                p = Path(__file__).resolve().parents[1] / 'core' / 'licencas.json'
            if p.exists():
                with open(p, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for entry in data:
                    slug = entry.get('slug') or ''
                    if not slug:
                        continue
                    prefix = slug.upper()
                    db_user = os.getenv(f'{prefix}_DB_USER', '') or config(f'{prefix}_DB_USER', default='')
                    db_password = os.getenv(f'{prefix}_DB_PASSWORD', '') or config(f'{prefix}_DB_PASSWORD', default='')
                    mods = json.dumps(entry.get('modulos', []) or [])
                    cur.execute(
                        """
                        INSERT INTO licencas_web (slug, cnpj, db_name, db_host, db_port, modulos, db_user, db_password)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (slug) DO UPDATE SET
                            cnpj=EXCLUDED.cnpj,
                            db_name=EXCLUDED.db_name,
                            db_host=EXCLUDED.db_host,
                            db_port=EXCLUDED.db_port,
                            modulos=EXCLUDED.modulos,
                            db_user=EXCLUDED.db_user,
                            db_password=EXCLUDED.db_password
                        """,
                        (
                            slug,
                            entry.get('cnpj', ''),
                            entry.get('db_name', ''),
                            entry.get('db_host', ''),
                            entry.get('db_port', ''),
                            mods,
                            db_user,
                            db_password,
                        )
                    )
        conn.commit()
        logger.warning("[LICENCAS_LOADER] bootstrap licencas_web criado e populado")
    except Exception as e:
        logger.warning("[LICENCAS_LOADER] bootstrap falhou: %s", e)
