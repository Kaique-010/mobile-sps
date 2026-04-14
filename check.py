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
                c.execute("SELECT * FROM django_migrations WHERE app='transportes'")
                print(alias, "migrations:")
                for row in c.fetchall():
                    print("  ", row)
            except Exception as e:
                print(alias, "error getting migrations:", e)

            try:
                c.execute("SELECT COUNT(*) FROM transportes_regraicms")
                print(alias, "transportes_regraicms count:", c.fetchone()[0])
            except Exception as e:
                print(alias, "error checking transportes_regraicms:", e)
