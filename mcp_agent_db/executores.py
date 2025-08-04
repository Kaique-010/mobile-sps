from django.db import connections

def executar_sql_com_slug(sql: str, slug: str) -> list:

    with connections['default'].cursor() as cursor:
        cursor.execute(sql)
        colunas = [col[0] for col in cursor.description]
        dados = cursor.fetchall()
    return [dict(zip(colunas, row)) for row in dados]
