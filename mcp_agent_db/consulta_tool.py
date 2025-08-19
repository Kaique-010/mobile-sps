import os
import django
from django.db import connection
from langchain.tools import tool
from .sql_generator import gerar_sql_da_pergunta
from .cache_manager import query_cache
from .conversation_memory import conversation_memory
from .schema_loader import carregar_schema
import json

# Remover django.setup() - será configurado pelo Django automaticamente
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
# django.setup()

@tool
def consulta_postgres_tool(pergunta: str, slug: str = "casaa") -> str:
    """
    Ferramenta para consultar banco PostgreSQL com geração automática de SQL.
    
    Args:
        pergunta: Pergunta em linguagem natural sobre os dados
        slug: Identificador do cliente/schema (padrão: casaa)
    
    Returns:
        Resultado da consulta formatado
    """
    return consultar_banco_dados_interno(pergunta, slug)

@tool
def consultar_banco_dados(pergunta: str, slug: str = "casaa") -> str:
    """
    Ferramenta principal para consultar banco de dados PostgreSQL.
    
    Args:
        pergunta: Pergunta em linguagem natural sobre os dados
        slug: Identificador do cliente/schema (padrão: casaa)
    
    Returns:
        Resultado da consulta formatado com insights e sugestões
    """
    return consultar_banco_dados_interno(pergunta, slug)

def consultar_banco_dados_interno(pergunta: str, slug: str = "casaa") -> str:
    """Função interna para consultar banco de dados"""
    try:
        print(f"🔍 Consultando banco para: {pergunta}")
        
        # Verificar cache primeiro
        resultado_cache = query_cache.get(pergunta, slug)
        if resultado_cache:
            print("📋 Resultado encontrado no cache")
            return resultado_cache
        
        # Carregar schema e metadados
        schema = carregar_schema(slug)
        if not schema:
            return f"❌ Schema não encontrado para slug: {slug}"
        
        metadados = schema.get('_metadados', {})
        print(f"📊 Metadados carregados:")
        print(f"  - Exemplos: {list(metadados.get('exemplos_consultas', {}).keys())}")
        print(f"  - Campos chave: {list(metadados.get('campos_chave', {}).keys())}")
        
        # Adicionar contexto específico baseado na pergunta
        pergunta_com_contexto = pergunta
        
        if "entidade" in pergunta.lower() and "tipo" in pergunta.lower():
            pergunta_com_contexto += "\n\nUSE: SELECT enti_tipo_enti, COUNT(*) as quantidade FROM entidades GROUP BY enti_tipo_enti"
            print("🎯 Contexto específico adicionado para entidades por tipo")
        elif "pedido" in pergunta.lower() and "cliente" in pergunta.lower():
            pergunta_com_contexto += "\n\nUSE: Consulte tabelas de pedidos e clientes, agrupe por cliente. Use CAST para converter tipos se necessário."
            print("🎯 Contexto específico adicionado para pedidos por cliente")
        
        # Gerar SQL com metadados
        sql = gerar_sql_da_pergunta(pergunta_com_contexto, slug)
        
        if sql.startswith("-- Erro"):
            return sql
        
        print(f"🔍 SQL gerado: {sql}")
        
        # Executar consulta
        with connection.cursor() as cursor:
            cursor.execute(sql)
            resultados = cursor.fetchall()
            colunas = [desc[0] for desc in cursor.description]
        
        # Processar resultados
        if not resultados:
            resposta = "Nenhum resultado encontrado."
        else:
            # Converter para formato legível
            dados_formatados = []
            for linha in resultados:
                linha_dict = dict(zip(colunas, linha))
                dados_formatados.append(linha_dict)
            
            # Adicionar à memória de conversa (método correto)
            conversation_memory.add_interaction(pergunta, "", sql, dados_formatados)
            
            # Gerar insights
            insights = gerar_insights(dados_formatados, pergunta)
            
            # Gerar sugestões contextuais
            sugestoes = conversation_memory.get_suggestions()
            
            # Formatar resposta
            resposta = formatar_resposta_consulta(sql, dados_formatados, insights, sugestoes)
        
        # Salvar no cache
        query_cache.set(pergunta, slug, resposta, sql)
        
        return resposta
        
    except Exception as e:
        error_msg = f"❌ Erro na consulta: {str(e)}"
        print(error_msg)
        return error_msg

def gerar_insights(dados: list, pergunta: str) -> str:
    """Gera insights inteligentes baseados nos dados"""
    if not dados:
        return ""
    
    insights = []
    
    # Análise básica
    total_registros = len(dados)
    insights.append(f"Total de registros: {total_registros}")
    
    # Análise específica para entidades por tipo
    if any('enti_tipo_enti' in str(item) for item in dados):
        tipos_encontrados = []
        for item in dados:
            if isinstance(item, dict):
                tipo = item.get('enti_tipo_enti')
                quantidade = item.get('quantidade') or item.get('count')
                if tipo and quantidade:
                    tipo_nome = {'CL': 'Clientes', 'VE': 'Vendedores', 'FO': 'Fornecedores'}.get(tipo, tipo)
                    tipos_encontrados.append(f"{tipo_nome}: {quantidade}")
        
        if tipos_encontrados:
            insights.append("Distribuição por tipo:")
            insights.extend([f"  - {tipo}" for tipo in tipos_encontrados])
    
    # Análise para pedidos por cliente
    if "cliente" in pergunta.lower() and "pedido" in pergunta.lower():
        if dados:
            # Tentar identificar campos de cliente e quantidade
            primeiro_item = dados[0]
            if isinstance(primeiro_item, dict):
                campos_cliente = [k for k in primeiro_item.keys() if 'cliente' in k.lower() or 'nome' in k.lower()]
                campos_quantidade = [k for k in primeiro_item.keys() if 'count' in k.lower() or 'quantidade' in k.lower() or 'total' in k.lower()]
                
                if campos_quantidade:
                    valores = [item.get(campos_quantidade[0], 0) for item in dados if isinstance(item.get(campos_quantidade[0]), (int, float))]
                    if valores:
                        insights.append(f"Estatísticas de pedidos:")
                        insights.append(f"  - Média: {sum(valores)/len(valores):.1f} pedidos por cliente")
                        insights.append(f"  - Máximo: {max(valores)} pedidos")
                        insights.append(f"  - Mínimo: {min(valores)} pedidos")
    
    # Análise de campos numéricos gerais
    for item in dados[:1]:  # Analisar primeiro item para estrutura
        if isinstance(item, dict):
            for campo, valor in item.items():
                if isinstance(valor, (int, float)) and campo not in ['id', 'codigo'] and 'count' not in campo.lower():
                    valores = [row.get(campo, 0) for row in dados if isinstance(row.get(campo), (int, float))]
                    if valores and len(valores) > 1:
                        insights.append(f"{campo.title()}: Média {sum(valores)/len(valores):.2f}, Máximo {max(valores)}, Mínimo {min(valores)}")
    
    return "\n".join(insights) if insights else ""

def formatar_resposta_consulta(sql: str, dados: list, insights: str, sugestoes: list) -> str:
    """Formata a resposta da consulta de forma estruturada"""
    resposta = f"📊 **Resultados da consulta:**\n\n"
   
    
    # Mostrar dados
    if len(dados) <= 10:
        resposta += "**Dados encontrados:**\n"
        for i, linha in enumerate(dados, 1):
            resposta += f"\n**Registro {i}:**\n"
            for coluna, valor in linha.items():
                resposta += f"- {coluna}: {valor}\n"
    else:
        resposta += f"**Resumo:** {len(dados)} registros encontrados\n\n"
        resposta += "**Primeiros 5 registros:**\n"
        for i, linha in enumerate(dados[:5], 1):
            resposta += f"\n**Registro {i}:**\n"
            for coluna, valor in linha.items():
                resposta += f"- {coluna}: {valor}\n"
    
    # Adicionar insights
    if insights:
        resposta += f"\n\n💡 **Insights:**\n{insights}"
    
    # Adicionar sugestões
    if sugestoes:
        resposta += f"\n\n🔮 **Sugestões para próximas consultas:**\n"
        for sugestao in sugestoes[:3]:  # Limitar a 3 sugestões
            resposta += f"- {sugestao}\n"
    
    return resposta
