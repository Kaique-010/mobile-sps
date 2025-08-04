from langchain.tools import tool
from .agente_inteligente_v2 import gerar_sql_da_pergunta
from .executores import executar_sql_com_slug
from .schema_loader import carregar_schema

@tool
def relatorio_estoque_baixo(slug: str) -> str:
    """
    Itens com estoque abaixo do mínimo ou abaixo de 2.
    """
    pergunta = "Quais produtos estão com estoque abaixo de 2 ou abaixo do estoque mínimo?"
    return gerar_e_executar_sql(pergunta, slug)

@tool
def contas_a_pagar_semana(slug: str) -> str:
    """
    Contas a pagar nos próximos 7 dias.
    """
    pergunta = "Quais contas a pagar vencem nos próximos 7 dias?"
    return gerar_e_executar_sql(pergunta, slug)

@tool
def sugestao_compras_estoque(slug: str) -> str:
    """
    Sugestão de compras com base em vendas dos últimos 30 dias e estoque atual.
    """
    pergunta = "Quais produtos tiveram mais de 10 unidades vendidas nos últimos 30 dias e estão com estoque baixo?"
    return gerar_e_executar_sql(pergunta, slug)

def gerar_e_executar_sql(pergunta: str, slug: str) -> str:
    schema = carregar_schema(slug)
    if not schema:
        return f"❌ Schema não encontrado para {slug}"
    
    sql = gerar_sql_da_pergunta(pergunta, slug)
    # Optional: forçar filtro empresa
    # sql = forcar_filtro_empresa(sql, slug)
    return executar_sql_com_slug(sql, slug)
