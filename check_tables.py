import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_name IN ('historico_workflow', 'workflow_setor');")
tables = cursor.fetchall()

print("Tabelas encontradas:")
for table in tables:
    print(f"- {table[0]}")

if len(tables) == 2:
    print("\n✅ Ambas as tabelas foram criadas com sucesso!")
else:
    print(f"\n❌ Apenas {len(tables)} tabela(s) encontrada(s)")