from langchain.prompts import ChatPromptTemplate
from langchain.chat_models import init_chat_model
from langchain_core.output_parsers import StrOutputParser
from .schema_loader import carregar_schema, formatar_schema_para_prompt
from .prompt_sql import TEMPLATE_SQL

from dotenv import load_dotenv
import re

load_dotenv()

model_llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")

def gerar_sql_da_pergunta(pergunta: str, slug: str) -> str:
    """Gera SQL para a pergunta usando schema do cliente"""
    try:
        # Carregar schema com metadados
        schema = carregar_schema(slug)
        if not schema:
            raise Exception(f"Schema não encontrado para slug: {slug}")
        
        # Extrair metadados
        metadados = schema.get('_metadados', {})
        print('📊 Metadados carregados:', metadados)
        exemplos_consultas = metadados.get('exemplos_consultas', {})
        campos_chave = metadados.get('campos_chave', {})
        
        # Adicionar contexto de metadados ao prompt
        contexto_metadados = "\n\nMETADADOS IMPORTANTES:\n"
        
        # Adicionar exemplos de consultas
        if exemplos_consultas:
            contexto_metadados += "EXEMPLOS DE CONSULTAS:\n"
            for categoria, exemplos in exemplos_consultas.items():
                contexto_metadados += f"- {categoria.upper()}:\n"
                for exemplo in exemplos:
                    contexto_metadados += f"  * {exemplo}\n"
        
        # Adicionar campos chave
        if campos_chave:
            contexto_metadados += "\nCAMPOS CHAVE POR CONTEXTO:\n"
            for contexto, info in campos_chave.items():
                contexto_metadados += f"- {contexto.upper()}: tabelas {info['tabelas']}, campos {info.get('campos_identificacao', [])}\n"
        
        # Adicionar informações específicas sobre tipos de entidade
        contexto_metadados += "\nINFORMAÇÕES ESPECÍFICAS:\n"
        contexto_metadados += "- Campo enti_tipo_enti na tabela entidades classifica tipos:\n"
        contexto_metadados += "  * 'CL' = Clientes\n"
        contexto_metadados += "  * 'VE' = Vendedores\n"
        contexto_metadados += "  * Para agrupar por tipo: GROUP BY enti_tipo_enti\n"
        
        print('📋 Contexto de metadados adicionado:', contexto_metadados[:200] + '...')
        
        # Formatar schema para o prompt
        schema_formatado = formatar_schema_para_prompt(schema)
        
        # Criar prompt com contexto aprimorado
        prompt = ChatPromptTemplate.from_template(TEMPLATE_SQL + contexto_metadados)
        
        chain = prompt | model_llm | StrOutputParser()
        
        sql_gerado = chain.invoke({
            "pergunta": pergunta,
            "schema": schema_formatado,
            "slug": slug
        })
        
        # Limpar SQL
        sql_limpo = re.sub(r'```sql\s*', '', sql_gerado)
        sql_limpo = re.sub(r'```\s*$', '', sql_limpo)
        sql_limpo = sql_limpo.strip()
        
        print('🔍 SQL gerado:', sql_limpo[:100] + '...')
        
        return sql_limpo
        
    except Exception as e:
        print(f"❌ Erro ao gerar SQL: {e}")
        return f"-- Erro ao gerar SQL: {str(e)}"