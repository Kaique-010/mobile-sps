# gerar_schema.py

import psycopg2
import sqlite3
import os
import json
from typing import Dict, List, Any

SCHEMA_DIR = "schemas"

# Configurações de exemplo para diferentes tipos de banco
DATABASES = {
    "casaa": {
        "tipo": "postgres",
        "host": "localhost",
        "port": 5432,
        "user": "postgres",
        "password": "@spartacus201@",
        "dbname": "casaa"
    },
    "spartacus": {
        "tipo": "postgres",
        "host": "localhost",
        "port": 5432,
        "user": "postgres",
        "password": "postgres",
        "dbname": "spartacus"
    },
    "cliente_sqlite": {
        "tipo": "sqlite",
        "caminho": "exemplo.db"
    },
    "cliente_teste": {
        "tipo": "sqlite",
        "caminho": "teste.db"
    },
    "cliente_mysql": {
        "tipo": "mysql",
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "senha",
        "dbname": "cliente_db"
    }
}

def conectar_db(config: Dict[str, Any]):
    """Conecta ao banco baseado no tipo configurado"""
    tipo = config.get("tipo", "postgres")
    
    if tipo == "postgres":
        return psycopg2.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            dbname=config["dbname"]
        )
    elif tipo == "sqlite":
        return sqlite3.connect(config["caminho"])
    elif tipo == "mysql":
        try:
            import mysql.connector
            return mysql.connector.connect(
                host=config["host"],
                port=config["port"],
                user=config["user"],
                password=config["password"],
                database=config["dbname"]
            )
        except ImportError:
            raise ImportError("mysql-connector-python não instalado. Execute: pip install mysql-connector-python")
    else:
        raise ValueError(f"Tipo de banco não suportado: {tipo}")

def extrair_schema_postgres(conexao):
    """Extrai schema do PostgreSQL"""
    cursor = conexao.cursor()
    cursor.execute("""
        SELECT 
            t.table_name,
            c.column_name,
            c.data_type,
            c.is_nullable,
            c.column_default,
            CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_primary_key
        FROM information_schema.tables t
        JOIN information_schema.columns c ON t.table_name = c.table_name
        LEFT JOIN (
            SELECT ku.table_name, ku.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage ku ON tc.constraint_name = ku.constraint_name
            WHERE tc.constraint_type = 'PRIMARY KEY'
        ) pk ON c.table_name = pk.table_name AND c.column_name = pk.column_name
        WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
        ORDER BY t.table_name, c.ordinal_position;
    """)
    return cursor.fetchall()

def extrair_schema_sqlite(conexao):
    """Extrai schema do SQLite"""
    cursor = conexao.cursor()
    
    # Obter lista de tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tabelas = cursor.fetchall()
    
    resultado = []
    for (tabela,) in tabelas:
        # Obter informações das colunas
        cursor.execute(f"PRAGMA table_info({tabela});")
        colunas = cursor.fetchall()
        
        for col in colunas:
            cid, nome, tipo, notnull, default_value, pk = col
            resultado.append((
                tabela,
                nome, 
                tipo,
                'NO' if notnull else 'YES',  # is_nullable
                default_value,
                bool(pk)  # is_primary_key
            ))
    
    return resultado

def extrair_schema(conexao, tipo_banco="postgres"):
    """Extrai schema baseado no tipo de banco"""
    if tipo_banco == "postgres":
        dados = extrair_schema_postgres(conexao)
    elif tipo_banco == "sqlite":
        dados = extrair_schema_sqlite(conexao)
    else:
        raise ValueError(f"Tipo de banco não suportado para extração: {tipo_banco}")
    
    schema = {}
    for row in dados:
        table_name, column_name, data_type, is_nullable, column_default, is_primary_key = row
        
        if table_name not in schema:
            schema[table_name] = {
                "colunas": [],
                "descricao": f"Tabela {table_name}"
            }
        
        schema[table_name]["colunas"].append({
            "nome": column_name,
            "tipo": data_type,
            "nullable": is_nullable == 'YES',
            "default": column_default,
            "primary_key": is_primary_key
        })
    
    return schema

def salvar_schema(slug, schema):
    os.makedirs(SCHEMA_DIR, exist_ok=True)
    caminho = os.path.join(SCHEMA_DIR, f"{slug}.json")
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    print(f"✅ Schema salvo em {caminho}")

# Dicionário de campos chave por contexto
CAMPOS_CHAVE = {
    "clientes": {
        "tabelas": ["entidades"],
        "campos_identificacao": ["enti_clie", "enti_nome", "enti_fant"],
        "campos_contato": ["enti_fone", "enti_celu", "enti_emai"],
        "campos_endereco": ["enti_ende", "enti_cida", "enti_esta", "enti_cep"],
        "campos_documento": ["enti_cnpj", "enti_cpf"]
    },
    "vendedores": {
        "tabelas": ["entidades"],
        "campos_identificacao": ["pedi_vend", "enti_nome", "enti_titpo_enti"],
       
    },
    "produtos": {
        "tabelas": ["produtos"],
        "campos_identificacao": ["prod_codi", "prod_nome"],
        "campos_preco": ["prod_prec", "prod_cust"],
        "campos_estoque": ["sapr_sald"]
    },
    "pedidos": {
        "tabelas": ["pedidosvenda"],
        "campos_identificacao": ["pedi_nume", "pedi_data"],
        "campos_cliente": ["pedi_forn"],
        "campos_vendedor": ["pedi_vend"],
        "campos_valor": ["pedi_tota"]
    }
}

def adicionar_metadados_schema(schema_dict):
    """Adiciona metadados sobre campos chave ao schema"""
    schema_dict["_metadados"] = {
        "campos_chave": CAMPOS_CHAVE,
        "descricao": "Metadados para facilitar consultas do agente",
        "exemplos_consultas": {
            "clientes": [
                "Campos principais: enti_clie (código), enti_nome (nome), enti_fant (fantasia)",
                "IMPORTANTE: Para pedidos/vendas, NÃO filtrar por enti_tipo_enti = 'CL'"
            ],
            "vendedores": [
             
                "USAR: SELECT enti_nome FROM entidades WHERE enti_tipo_enti = 'VE'",
                "IMPORTANTE: Para pedidos/vendas, NÃO filtrar por enti_tipo_enti = 'VE'"
            ],
            "produtos": [
                "Para buscar produtos: SELECT prod_nome FROM produtos",
                "Para estoque: SELECT sapr_sald FROM saldosprodutos"
            ],
            "pedidos": [
                "Para buscar pedidos: SELECT pedi_nume, pedi_data FROM pedidosvenda",
                "Relacionar com cliente: JOIN entidades ON pedi_forn = enti_clie",
                "Relacionar com produto: JOIN produtos ON pedi_prod = prod_codi",
                "Relacionar com vendedor: JOIN entidades ON pedi_vend = enti_clie",
                "CRÍTICO: NUNCA filtrar por enti_tipo_enti em consultas de pedidos",
                "SEMPRE incluir enti_tipo_enti no SELECT para mostrar o tipo da entidade",
                "Uma entidade pode ser CL (cliente), FO (fornecedor), VE (vendedor) ou AM (ambos)"
            ],
            "regras_filtros": [
                "NUNCA usar WHERE enti_tipo_enti = 'CL' em consultas de pedidos/vendas",
                "NUNCA usar WHERE enti_tipo_enti = 'FO' em consultas de pedidos/vendas", 
                "SEMPRE incluir enti_tipo_enti no SELECT para discriminar tipos",
                "Entidades podem ter múltiplos tipos simultaneamente",
                "Para agrupar por tipo, usar GROUP BY enti_tipo_enti (sem WHERE)"
            ]
        }
    }
    return schema_dict

def gerar_schema(slug):
    """Gera o schema para um banco específico"""
    print(f"🔄 Gerando schema para: {slug}")
    
    try:
        # Conectar ao banco - CORRIGIDO
        config = DATABASES.get(slug)
        if not config:
            print(f"❌ Configuração não encontrada para slug: {slug}")
            return None
            
        conn = conectar_db(config)
        if not conn:
            return None
        
        # Extrair schema
        schema = extrair_schema(conn, config.get("tipo", "postgres"))
        
        # Adicionar metadados
        schema = adicionar_metadados_schema(schema)
        
        # Salvar schema
        salvar_schema(slug, schema)
        
        conn.close()
        print(f"✅ Schema gerado com sucesso: {slug}")
        return schema  # Retornar o schema em vez de True
        
    except Exception as e:
        print(f"❌ Erro ao gerar schema: {e}")
        return None

def criar_banco_exemplo_sqlite():
    """Cria um banco SQLite de exemplo para testar"""
    print("🛠️ Criando banco SQLite de exemplo...")
    
    conn = sqlite3.connect("exemplo.db")
    cursor = conn.cursor()
    
    # Criar tabelas de exemplo
    cursor.executescript("""
        DROP TABLE IF EXISTS pedidos;
        DROP TABLE IF EXISTS clientes;
        DROP TABLE IF EXISTS produtos;
        
        CREATE TABLE clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE,
            data_cadastro DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            preco DECIMAL(10,2),
            categoria TEXT,
            ativo BOOLEAN DEFAULT 1
        );
        
        CREATE TABLE pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            produto_id INTEGER,
            quantidade INTEGER DEFAULT 1,
            valor_total DECIMAL(10,2),
            data_pedido DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pendente'
        );
        
        -- Dados de exemplo
        INSERT INTO clientes (nome, email) VALUES 
            ('João Silva', 'joao@email.com'),
            ('Maria Santos', 'maria@email.com');
            
        INSERT INTO produtos (nome, preco, categoria) VALUES 
            ('Notebook', 2500.00, 'eletrônicos'),
            ('Mouse', 50.00, 'acessórios');
            
        INSERT INTO pedidos (cliente_id, produto_id, quantidade, valor_total) VALUES 
            (1, 1, 1, 2500.00),
            (2, 2, 2, 100.00);
    """)
    
    conn.commit()
    conn.close()
    print("✅ Banco SQLite criado: exemplo.db")

def testar_sistema_completo():
    """Testa o sistema completo de geração de schema"""
    print("🚀 TESTANDO SISTEMA DE GERAÇÃO DE SCHEMA")
    print("=" * 50)
    
    # Criar banco de exemplo
    criar_banco_exemplo_sqlite()
    
    # Gerar schema
    schema = gerar_schema("casaa")
    
    if not schema:
        print("❌ Falha ao gerar schema")
        return None
    
    # Mostrar resultado
    print("\n📋 SCHEMA GERADO:")
    tabelas_mostradas = 0
    for tabela, info in schema.items():
        if tabela.startswith('_'):  # Pular metadados na exibição
            continue
            
        if tabelas_mostradas >= 5:  # Mostrar apenas as primeiras 5 tabelas
            total_tabelas = len([t for t in schema.keys() if not t.startswith('_')])
            print(f"\n... e mais {total_tabelas - 5} tabelas")
            break
            
        print(f"\n🔹 {tabela}:")
        colunas = info.get('colunas', [])
        for i, coluna in enumerate(colunas):
            if i >= 5:  # Mostrar apenas as primeiras 5 colunas
                print(f"  ... e mais {len(colunas) - 5} colunas")
                break
            pk = " (PK)" if coluna['primary_key'] else ""
            nullable = "NULL" if coluna['nullable'] else "NOT NULL"
            print(f"  - {coluna['nome']}: {coluna['tipo']} {nullable}{pk}")
        
        tabelas_mostradas += 1
    
    # Mostrar metadados se existirem
    if '_metadados' in schema:
        print("\n🔑 METADADOS INCLUÍDOS:")
        metadados = schema['_metadados']
        campos_chave = metadados.get('campos_chave', {})
        for contexto, info in campos_chave.items():
            print(f"  📋 {contexto}: {', '.join(info['tabelas'])}")
        print(f"  ✅ Total de {len(campos_chave)} contextos com metadados")
    
    return schema

if __name__ == "__main__":
    # Testar sistema completo
    testar_sistema_completo()
