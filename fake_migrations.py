import os
import django
from core.licencas_loader import carregar_licencas_dict
from django.db import connections
from core.management.commands.migrate_tenant_app import montar_db_config
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

licencas = carregar_licencas_dict()
for l in licencas:
    if l['slug'] in ['saveweb004', 'saveweb005']:
        alias = l['slug']
        connections.databases[alias] = montar_db_config(l)
        
        print(f"Faking migrations on {alias}...")
        
        # Fake 0002
        call_command(
            "migrate",
            "transportes",
            "0002_regraicms",
            database=alias,
            fake=True,
            interactive=False,
        )
        
        # Fake 0003
        call_command(
            "migrate",
            "transportes",
            "0003_mdfedocumento",
            database=alias,
            fake=True,
            interactive=False,
        )
        
        print(f"Running normal migrate on {alias} to apply 0004...")
        call_command(
            "migrate",
            "transportes",
            database=alias,
            interactive=False,
        )
