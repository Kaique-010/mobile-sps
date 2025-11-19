from django.db import connections

class NotaLegadoReader:

    def __init__(self, banco):
        self.banco = banco

    def listar_notas(self, limite=1000):
        cursor = connections[self.banco].cursor()
        cursor.execute(
            """
            SELECT *
            FROM nfevv
            WHERE b11_tpnf = 1   
            ORDER BY b09_demi DESC
            LIMIT %s
            """,
            [limite],
        )

        colunas = [c[0] for c in cursor.description]
        resultados = cursor.fetchall()

        return [dict(zip(colunas, r)) for r in resultados]

    def listar_itens_por_nota(self, nota_id):
        cursor = connections[self.banco].cursor()
        cursor.execute(
            """
            SELECT *
            FROM infvv
            WHERE id = %s
            ORDER BY nitem
            """,
            [nota_id],
        )

        colunas = [c[0] for c in cursor.description]
        resultados = cursor.fetchall()
        return [dict(zip(colunas, r)) for r in resultados]