from collections import defaultdict
from ..models import DashboardCentroCustoAnual

class DashboardService:
    @staticmethod
    def montar_arvore():
        """
        Monta estrutura hierárquica completa a partir da view dashboardcentrocustoanual.
        """
        dados = list(DashboardCentroCustoAnual.objects.all().values())
        filhos_map = defaultdict(list)
        raiz = []

        for item in dados:
            item["filhos"] = []
            pai = item.get("codigo_pai")
            if pai:
                filhos_map[pai].append(item)
            else:
                raiz.append(item)

        def preencher_filhos(lista):
            for item in lista:
                item["filhos"] = filhos_map.get(item["codigo"], [])
                if item["filhos"]:
                    preencher_filhos(item["filhos"])

        preencher_filhos(raiz)
        return raiz

    @staticmethod
    def _flatten(lista):
        for item in lista:
            yield item
            yield from DashboardService._flatten(item.get("filhos", []))
