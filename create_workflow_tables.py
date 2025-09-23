import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()

# SQL para criar a tabela historico_workflow
create_historico_sql = """
CREATE TABLE IF NOT EXISTS historico_workflow (
    hist_id SERIAL PRIMARY KEY,
    hist_empr INTEGER NOT NULL,
    hist_fili INTEGER NOT NULL,
    hist_orde INTEGER NOT NULL,
    hist_seto_orig INTEGER,
    hist_seto_dest INTEGER NOT NULL,
    hist_usua INTEGER NOT NULL,
    hist_data TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
"""

# SQL para criar a tabela workflow_setor
create_workflow_sql = """
CREATE TABLE IF NOT EXISTS workflow_setor (
    wkfl_id SERIAL PRIMARY KEY,
    wkfl_seto_orig INTEGER NOT NULL,
    wkfl_seto_dest INTEGER NOT NULL,
    wkfl_orde INTEGER DEFAULT 1,
    wkfl_ativo BOOLEAN DEFAULT TRUE,
    UNIQUE(wkfl_seto_orig, wkfl_seto_dest)
);
"""

try:
    print("Criando tabela historico_workflow...")
    cursor.execute(create_historico_sql)
    
    print("Criando tabela workflow_setor...")
    cursor.execute(create_workflow_sql)
    
    print("✅ Tabelas criadas com sucesso!")
    
    # Verificar se as tabelas foram criadas
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_name IN ('historico_workflow', 'workflow_setor');")
    tables = cursor.fetchall()
    
    print(f"Tabelas encontradas: {[table[0] for table in tables]}")
    
except Exception as e:
    print(f"❌ Erro ao criar tabelas: {e}")