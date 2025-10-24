from ..models import DashboardCentroCustoAnual
from ..serializers import DashboardCentroCustoAnualSerializer
from django.db import connections

class DashboardService:
    @staticmethod

    def montar_arvore(banco, mes_ini=None, mes_fim=None, nivel=None, tipo=None, busca=None):
        with connections[banco].cursor() as cursor:
            filtros = []
            if mes_ini and mes_fim:
                filtros.append(f"mes_num BETWEEN {int(mes_ini)} AND {int(mes_fim)}")
            elif mes_ini:
                filtros.append(f"mes_num = {int(mes_ini)}")
            if nivel:
                filtros.append(f"nivel = {int(nivel)}")
            if tipo:
                filtros.append(f"tipo = '{tipo}'")
            if busca:
                busca = busca.upper()
                filtros.append(f"(UPPER(nome) LIKE '%{busca}%' OR expandido LIKE '%{busca}%')")
            
            where = f"WHERE {' AND '.join(filtros)}" if filtros else ""
            cursor.execute(f"SELECT * FROM dashboardcentrocustoanual {where} ORDER BY expandido, mes_num")
            rows = DashboardService.dictfetchall(cursor)

        objs = [DashboardCentroCustoAnual(**r) for r in rows]
        return DashboardService._montar_hierarquia(objs)


    @staticmethod
    def _montar_hierarquia(registros):
        """
        Monta árvore de centros de custo.
        """
        mapa = {r.codigo: r for r in registros}
        raiz = []

        for r in registros:
            if r.codigo_pai and r.codigo_pai in mapa:
                pai = mapa[r.codigo_pai]
                if not hasattr(pai, "filhos"):
                    pai.filhos = []
                pai.filhos.append(r)
            else:
                raiz.append(r)
        return raiz

    @staticmethod
    def _flatten(lista):
        for item in lista:
            yield {
                "codigo": item.codigo,
                "orcado": item.orcado,
                "realizado": item.realizado,
                "diferenca": item.diferenca,
            }
            if hasattr(item, "filhos"):
                yield from DashboardService._flatten(item.filhos)

    @staticmethod
    def dictfetchall(cursor):
        cols = [col[0] for col in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
