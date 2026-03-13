from CFOP.models import CFOP, MapaCFOP


class CFOPResolver:

    def __init__(self, banco=None):
        self.banco = banco

    def resolver(self, tipo_oper, uf_origem, uf_destino):

        qs = MapaCFOP.objects

        if self.banco:
            qs = qs.using(self.banco)

        mapa = qs.select_related("cfop").filter(
            tipo_oper=tipo_oper,
            uf_origem=uf_origem,
            uf_destino=uf_destino
        ).first()

        if mapa:
            return mapa.cfop

        if tipo_oper == "VENDA":

            cod = "5102" if uf_origem == uf_destino else "6102"

            qs_cfop = CFOP.objects

            if self.banco:
                qs_cfop = qs_cfop.using(self.banco)

            return qs_cfop.filter(cfop_codi=cod).first()

        return None