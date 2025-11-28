# importador_produtos/services/resolvers_fk.py
from Produtos.models import Produtos
from Produtos.models import Marca
from Produtos.models import GrupoProduto, SubgrupoProduto, FamiliaProduto
from Produtos.models import UnidadeMedida


class ResolvedorFK:
    def __init__(self, row, db):
        self.row = row
        self.db = db

    def normalizar_nome(self, nome):
        return str(nome).strip().upper()

    def resolve_unidade(self, nome):
        nome = self.normalizar_nome(nome or "UN")
        un = UnidadeMedida.objects.using(self.db).filter(unid_codi__iexact=nome).first()

        if not un:
            un = UnidadeMedida.objects.using(self.db).create(
                unid_codi=nome,
                unid_desc=nome
            )
        return un

    def resolve_marca(self, nome):
        if not nome:
            return None

        nome = self.normalizar_nome(nome)
        m = Marca.objects.using(self.db).filter(nome__iexact=nome).first()

        if not m:
            maior = Marca.objects.using(self.db).order_by('-codigo').first()
            proximo = (maior.codigo + 1) if maior and isinstance(maior.codigo, int) else 1
            m = Marca.objects.using(self.db).create(codigo=proximo, nome=nome)

        return m

    def resolve_grupo(self, nome):
        if not nome:
            return None

        nome = self.normalizar_nome(nome)
        g = GrupoProduto.objects.using(self.db).filter(descricao__iexact=nome).first()

        if not g:
            base = nome[:3].upper()
            # Se já existir com o código base, reaproveita
            g = GrupoProduto.objects.using(self.db).filter(codigo=base).first()
            if g:
                return g
            codigo = base
            i = 1
            while GrupoProduto.objects.using(self.db).filter(codigo=codigo).exists():
                codigo = f"{base}{i}"
                i += 1
            g = GrupoProduto.objects.using(self.db).create(
                codigo=codigo,
                descricao=nome
            )
        return g

    def resolve_subgrupo(self, nome):
        if not nome:
            return None

        nome = self.normalizar_nome(nome)
        sg = SubgrupoProduto.objects.using(self.db).filter(descricao__iexact=nome).first()

        if not sg:
            base = nome[:3].upper()
            sg = SubgrupoProduto.objects.using(self.db).filter(codigo=base).first()
            if sg:
                return sg
            codigo = base
            i = 1
            while SubgrupoProduto.objects.using(self.db).filter(codigo=codigo).exists():
                codigo = f"{base}{i}"
                i += 1
            sg = SubgrupoProduto.objects.using(self.db).create(
                codigo=codigo,
                descricao=nome
            )
        return sg

    def resolve_familia(self, nome):
        if not nome:
            return None

        nome = self.normalizar_nome(nome)
        f = FamiliaProduto.objects.using(self.db).filter(descricao__iexact=nome).first()

        if not f:
            base = nome[:3].upper()
            f = FamiliaProduto.objects.using(self.db).filter(codigo=base).first()
            if f:
                return f
            codigo = base
            i = 1
            while FamiliaProduto.objects.using(self.db).filter(codigo=codigo).exists():
                codigo = f"{base}{i}"
                i += 1
            f = FamiliaProduto.objects.using(self.db).create(
                codigo=codigo,
                descricao=nome
            )
        return f

    def resolver(self):
        row = self.row.copy()

        row["prod_unme"] = self.resolve_unidade(row.get("prod_unme"))
        row["prod_marc"] = self.resolve_marca(row.get("prod_marc"))
        row["prod_grup"] = self.resolve_grupo(row.get("prod_grup"))
        row["prod_sugr"] = self.resolve_subgrupo(row.get("prod_sugr"))
        row["prod_fami"] = self.resolve_familia(row.get("prod_fami"))

        return row
