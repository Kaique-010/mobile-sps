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

    logger.warning("[LICENCAS_LOADER] INICIO alias=%s db=%s@%s",
                   alias, conf.get('NAME'), conf.get('HOST'))

    # Garantir existência da tabela
    _bootstrap_licencas_web_if_missing()

    resultado = []
    total_rows = 0

    try:
        with connections[alias].cursor() as cur:
            cur.execute("""
                SELECT slug, cnpj, db_name, db_host, db_port, modulos,
                       db_user, db_password
                FROM licencas_web
                ORDER BY slug
            """)
            rows = cur.fetchall()

            for row in rows:
                total_rows += 1

                slug, cnpj, db_name, db_host, db_port, modulos, db_user, db_password = row

                logger.warning("[ITEM] slug=%s cnpj=%s host=%s", slug, cnpj, db_host)

                # Normaliza CNPJ
                norm_doc = _normalize_doc(cnpj or "")
                if not (norm_doc.isdigit() and len(norm_doc) == 14):
                    logger.error("[DESCARTADO] slug=%s motivo=CNPJ inválido=%s norm=%s",
                                 slug, cnpj, norm_doc)
                    continue

                # Valida credenciais
                if not db_user or not db_password:
                    logger.error("[DESCARTADO] slug=%s motivo=credenciais faltando user=%s pass=%s",
                                 slug, db_user, db_password)
                    continue

                if not db_host:
                    logger.error("[DESCARTADO] slug=%s motivo=db_host vazio", slug)
                    continue

                # Monta item final
                item = {
                    "slug": (slug or "").strip().lower(),
                    "cnpj": norm_doc,
                    "db_name": db_name or slug,
                    "db_host": db_host or default_host,
                    "db_port": db_port or default_port,
                    "db_user": db_user,
                    "db_password": db_password,
                    "modulos": modulos or "[]",
                }

                resultado.append(item)

                logger.warning("[OK] slug=%s cnpj=%s host=%s db=%s",
                               item["slug"], item["cnpj"], item["db_host"], item["db_name"])

    except Exception as e:
        logger.error("[LICENCAS_LOADER] ERRO leitura tabela: %s", e)
        return []

    logger.warning("[LICENCAS_LOADER] FINAL count_total=%s carregadas=%s",
                   total_rows, len(resultado))

    logger.warning("[LICENCAS_LOADER] SLUGS: %s",
                   [i["slug"] for i in resultado])

    return resultado


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
