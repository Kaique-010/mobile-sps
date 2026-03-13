from decimal import Decimal
from ..models import TabelaICMS


class ICMSTableResolver:

    def __init__(self, banco=None):
        self.banco = banco

    def _d(self, v):
        if v is None:
            return None
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        return v.quantize(Decimal("0.01"))

    def resolver(self, uf_origem, uf_destino, empresa_id=None):

        qs = TabelaICMS.objects

        if self.banco:
            qs = qs.using(self.banco)

        filtros = {
            "uf_origem": uf_origem,
            "uf_destino": uf_destino
        }

        if empresa_id:
            filtros["empresa"] = empresa_id

        tabela = qs.filter(**filtros).first()

        if not tabela:
            return {
                "icms": None,
                "st_aliq": None,
                "mva_st": None,
            }

        mesma_uf = uf_origem == uf_destino

        return {
            "icms": self._d(
                tabela.aliq_interna if mesma_uf else tabela.aliq_inter
            ),
            "st_aliq": self._d(
                tabela.aliq_interna if mesma_uf else tabela.aliq_inter
            ),
            "mva_st": self._d(tabela.mva_st),
        }
