# importador_produtos/services/upsert_produto.py
from Produtos.models import Produtos


class UpsertProduto:
    def __init__(self, row, empresa, db):
        self.row = row
        self.empresa = empresa
        self.db = db

    def executar(self):
        codigo = self.row.get("prod_codi")
        prod = Produtos.objects.using(self.db).filter(prod_codi=codigo).first() if codigo else None

        dados = {
            "prod_empr": self.empresa,
            "prod_nome": self.row["prod_nome"],
            "prod_unme": self.row["prod_unme"],
            "prod_marc": self.row["prod_marc"],
            "prod_grup": self.row["prod_grup"],
            "prod_sugr": self.row["prod_sugr"],
            "prod_fami": self.row["prod_fami"],
            "prod_loca": self.row.get("prod_loca"),
            "prod_ncm": self.row.get("prod_ncm"),
            "prod_gtin": self.row.get("prod_gtin") or "SEM GTIN",
            "prod_orig_merc": self.row.get("prod_orig_merc", "0")
        }

        if not prod:
            nome = (self.row.get("prod_nome") or "").strip()
            empresa_str = str(self.empresa)
            existente_por_nome = Produtos.objects.using(self.db).filter(prod_empr=empresa_str, prod_nome__iexact=nome).first() if nome else None
            if existente_por_nome:
                for k, v in dados.items():
                    setattr(existente_por_nome, k, v)
                existente_por_nome.save(using=self.db)
                return existente_por_nome, False
            ultimo = (
                Produtos.objects.using(self.db)
                .filter(prod_empr=empresa_str)
                .order_by('-prod_codi')
                .first()
            )
            try:
                proximo = int(getattr(ultimo, 'prod_codi', '0')) + 1 if (ultimo and str(getattr(ultimo, 'prod_codi', '')).isdigit()) else 1
            except Exception:
                proximo = 1
            while Produtos.objects.using(self.db).filter(prod_codi=str(proximo), prod_empr=empresa_str).exists():
                proximo += 1
            novo_codigo = str(proximo)
            novo = Produtos.objects.using(self.db).create(prod_codi=novo_codigo, **dados)
            return novo, True

        for k, v in dados.items():
            setattr(prod, k, v)
        prod.save(using=self.db)
        return prod, False
