from Produtos.models import Ncm


class NCMResolver:

    def __init__(self, banco=None, ncm_db=None):
        self.banco = banco
        self.ncm_db = ncm_db

    def resolver(self, produto):

        if not produto.prod_ncm:
            return None

        cod = str(produto.prod_ncm).replace(".", "")

        bancos = []
        if self.banco:
            bancos.append(self.banco)
        if self.ncm_db and self.ncm_db not in bancos:
            bancos.append(self.ncm_db)
        if not self.ncm_db:
            try:
                from core.utils import get_ncm_master_db
                master = get_ncm_master_db(self.banco or "default")
                if master and master not in bancos:
                    bancos.append(master)
            except Exception:
                pass

        candidatos = [cod]
        if len(cod) == 8:
            candidatos.append(f"{cod[:4]}.{cod[4:6]}.{cod[6:]}")

        for banco in bancos or [None]:
            qs = Ncm.objects
            if banco:
                qs = qs.using(banco)
            for c in candidatos:
                ncm = qs.filter(ncm_codi=c).first()
                if ncm:
                    return ncm
            try:
                from django.db.models import F, Value
                from django.db.models.functions import Replace
                ncm = (
                    qs.annotate(
                        _ncm_norm=Replace(
                            Replace(F("ncm_codi"), Value("."), Value("")),
                            Value(" "),
                            Value(""),
                        )
                    )
                    .filter(_ncm_norm=cod)
                    .first()
                )
                if ncm:
                    return ncm
            except Exception:
                pass

        return None
