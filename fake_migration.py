import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()

try:
    # Verificar se a migração já existe
    cursor.execute("""
        SELECT COUNT(*) FROM django_migrations 
        WHERE app = 'OrdemdeServico' AND name = '0002_historicoworkflow_workflowsetor';
    """)
    
    count = cursor.fetchone()[0]
    
    if count == 0:
        # Inserir registro da migração
        cursor.execute("""
            INSERT INTO django_migrations (app, name, applied) 
            VALUES ('OrdemdeServico', '0002_historicoworkflow_workflowsetor', NOW());
        """)
        print("✅ Migração 0002 marcada como aplicada!")
    else:
        print("ℹ️ Migração 0002 já estava marcada como aplicada")
    
    # Verificar resultado final
    cursor.execute("""
        SELECT app, name, applied FROM django_migrations 
        WHERE app = 'OrdemdeServico' ORDER BY applied;
    """)
    
    migrations = cursor.fetchall()
    print("\nMigrações do OrdemdeServico:")
    for migration in migrations:
        print(f"  - {migration[1]} (aplicada em {migration[2]})")
        
except Exception as e:
    print(f"❌ Erro: {e}")