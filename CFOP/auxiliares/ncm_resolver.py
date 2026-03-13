from Produtos.models import Ncm


class NCMResolver:

    def __init__(self, banco=None):
        self.banco = banco

    def resolver(self, produto):

        if not produto.prod_ncm:
            return None

        cod = str(produto.prod_ncm).replace(".", "")

        qs = Ncm.objects

        if self.banco:
            qs = qs.using(self.banco)

        ncm = qs.filter(ncm_codi=cod).first()

        if ncm:
            return ncm

        # tenta formato pontuado
        if len(cod) == 8:
            cod_dotted = f"{cod[:4]}.{cod[4:6]}.{cod[6:]}"
            return qs.filter(ncm_codi=cod_dotted).first()

        return None