import os
import django
from core.licencas_loader import carregar_licencas_dict
from django.db import connections
from core.management.commands.migrate_tenant_app import montar_db_config

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

licencas = carregar_licencas_dict()
for l in licencas:
    if l['slug'] in ['saveweb004', 'saveweb005']:
        alias = l['slug']
        connections.databases[alias] = montar_db_config(l)
        with connections[alias].cursor() as c:
            try:
                c.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                      AND table_name LIKE 'transportes_%' OR table_name LIKE 'mdfe%' OR table_name LIKE 'motorista%' OR table_name LIKE 'tipos_documentos_motoristas%'
                """)
                tables = [r[0] for r in c.fetchall()]
                print(f"[{alias}] Tables: {tables}")
            except Exception as e:
                print(alias, "error getting tables:", e)
