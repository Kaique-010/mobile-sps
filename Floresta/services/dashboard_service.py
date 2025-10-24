from collections import defaultdict
from ..models import DashboardCentroCustoAnual
import logging

logger = logging.getLogger(__name__)

class DashboardService:
    @staticmethod
    def montar_arvore(banco=None):
        """
        Monta estrutura hierárquica completa a partir da view dashboardcentrocustoanual.
        """
        if banco:
            dados = list(DashboardCentroCustoAnual.objects.using(banco).all().values())
            logger.info(f"🔍 [DASHBOARD] Banco: {banco} - Registros encontrados: {len(dados)}")
        else:
            dados = list(DashboardCentroCustoAnual.objects.all().values())
            logger.info(f"🔍 [DASHBOARD] Banco padrão - Registros encontrados: {len(dados)}")
        
        if dados:
            logger.info(f"🔍 [DASHBOARD] Primeiro registro: {dados[0]}")
        else:
            logger.warning(f"⚠️ [DASHBOARD] Nenhum dado encontrado na tabela dashboardcentrocustoanual")
            
        filhos_map = defaultdict(list)
        raiz = []

        for item in dados:
            item["filhos"] = []
            pai = item.get("codigo_pai")
            if pai:
                filhos_map[str(pai)].append(item)
            else:
                raiz.append(item)

        def preencher_filhos(lista):
            for item in lista:
                codigo_str = str(item["codigo"])
                item["filhos"] = filhos_map.get(codigo_str, [])
                if item["filhos"]:
                    preencher_filhos(item["filhos"])

        preencher_filhos(raiz)
        return raiz

    @staticmethod
    def _flatten(lista):
        for item in lista:
            yield item
            yield from DashboardService._flatten(item.get("filhos", []))
