"""
Função para carregar schema
"""

import json
import os
from typing import Dict, Optional

def carregar_schema(slug: str) -> Optional[Dict]:
    """
    Carrega schema de um cliente específico
    
    Args:
        slug: Identificador do cliente (ex: 'cliente_abc', 'spartacus')
        
    Returns:
        Dict com schema ou None se não encontrado
    """
    # Usar caminho absoluto baseado na localização deste arquivo
    base_dir = os.path.dirname(os.path.abspath(__file__))
    caminho = os.path.join(base_dir, "schemas", f"{slug}.json")
    
    try:
        if not os.path.exists(caminho):
            print(f"⚠️ Schema não encontrado: {caminho}")
            return None
            
        with open(caminho, "r", encoding="utf-8") as f:
            schema = json.load(f)
            print(f"✅ Schema carregado: {slug} ({len(schema)} tabelas)")
            return schema
            
    except json.JSONDecodeError as e:
        print(f"❌ Erro ao decodificar JSON: {e}")
        return None
    except Exception as e:
        print(f"❌ Erro ao carregar schema: {e}")
        return None

def listar_schemas_disponiveis() -> list:
    """
    Lista todos os schemas disponíveis no diretório schemas/
    
    Returns:
        Lista com nomes dos schemas (sem extensão .json)
    """
    # Usar caminho absoluto baseado na localização deste arquivo
    base_dir = os.path.dirname(os.path.abspath(__file__))
    schemas_dir = os.path.join(base_dir, "schemas")
    
    if not os.path.exists(schemas_dir):
        return []
    
    schemas = []
    for arquivo in os.listdir(schemas_dir):
        if arquivo.endswith('.json'):
            schemas.append(arquivo[:-5])  # Remove .json
    
    return schemas

def formatar_schema_para_prompt(schema: Dict) -> str:
    """
    Formata schema para uso em prompts do LLM incluindo metadados
    """
    if not schema:
        return "Nenhum schema disponível"
    
    linhas = []
    linhas.append("=== SCHEMA DO BANCO DE DADOS ===\n")
    
    # Adicionar metadados se existirem
    metadados = schema.get('_metadados', {})
    if metadados:
        campos_chave = metadados.get('campos_chave', {})
        exemplos = metadados.get('exemplos_consultas', {})
        
        linhas.append("🔑 CAMPOS CHAVE POR CONTEXTO:")
        for contexto, info in campos_chave.items():
            linhas.append(f"\n📋 {contexto.upper()}:")
            linhas.append(f"   Tabelas: {', '.join(info['tabelas'])}")
            for tipo_campo, campos in info.items():
                if tipo_campo != 'tabelas':
                    linhas.append(f"   {tipo_campo}: {', '.join(campos)}")
        
        linhas.append("\n💡 EXEMPLOS DE CONSULTAS:")
        for contexto, exemplo_list in exemplos.items():
            linhas.append(f"\n📝 {contexto.upper()}:")
            for exemplo in exemplo_list:
                linhas.append(f"   - {exemplo}")
        
        linhas.append("\n" + "="*50)
    
    linhas.append("\n📊 TABELAS DISPONÍVEIS:")
    
    for tabela, info in schema.items():
        if tabela.startswith('_'):  # Pular metadados
            continue
            
        colunas = info.get('colunas', [])
        linhas.append(f"\n🔹 {tabela}:")
        
        # Separar colunas por tipo
        pks = [col for col in colunas if col.get('primary_key')]
        importantes = [col for col in colunas if any(palavra in col['nome'].lower() 
                      for palavra in ['nome', 'desc', 'data', 'valor', 'prec', 'quan'])]
        outras = [col for col in colunas if col not in pks and col not in importantes]
        
        if pks:
            linhas.append("   🔑 Chaves primárias:")
            for col in pks:
                linhas.append(f"      - {col['nome']} ({col['tipo']})")
        
        if importantes:
            linhas.append("   ⭐ Campos importantes:")
            for col in importantes:
                linhas.append(f"      - {col['nome']} ({col['tipo']})")
        
        if len(outras) <= 10:  # Mostrar todas se poucas
            linhas.append("   📝 Outros campos:")
            for col in outras:
                linhas.append(f"      - {col['nome']} ({col['tipo']})")
        else:  # Resumir se muitas
            linhas.append(f"   📝 Outros campos ({len(outras)}): {', '.join([col['nome'] for col in outras[:5]])}...")
    
    return "\n".join(linhas)