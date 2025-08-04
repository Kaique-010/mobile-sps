import re

def forcar_filtro_empresa(sql: str, slug: str) -> str:
    """Força filtro de empresa nas queries quando necessário"""
    # Mapear slug para código da empresa
    empresa_map = {
        "casaa": 1,
        "spartacus": 2,
        "cliente_teste": 3
    }
    
    codigo_empresa = empresa_map.get(slug)
    if not codigo_empresa:
        return sql
    
    # Se a query já tem filtro de empresa, não modificar
    if "pedi_empr" in sql.lower():
        return sql
    
    # Adicionar filtro WHERE ou AND conforme necessário
    if "WHERE" in sql.upper():
        sql = sql.replace("WHERE", f"WHERE pedi_empr = {codigo_empresa} AND")
    elif "FROM" in sql.upper() and "pedidosvenda" in sql.lower():
        # Adicionar WHERE após FROM pedidosvenda
        sql = re.sub(
            r"(FROM\s+pedidosvenda[^\s]*)", 
            f"\\1 WHERE pedi_empr = {codigo_empresa}", 
            sql, 
            flags=re.IGNORECASE
        )
    
    return sql