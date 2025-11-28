# importador_produtos/services/upsert_precos.py
from Produtos.models import Tabelaprecos, Tabelaprecoshist
from django.db import IntegrityError
from django.utils import timezone


class UpsertPrecos:
    def __init__(self, produto, row, empresa, filial, db):
        self.produto = produto
        self.row = row
        self.empresa = empresa
        self.filial = filial
        self.db = db

    def executar(self):
        base = self.row.get("preco")
        compra = self.row.get("preco_compra") if self.row.get("preco_compra") is not None else base
        vista = self.row.get("preco_vista") if self.row.get("preco_vista") is not None else base
        prazo = self.row.get("preco_prazo") if self.row.get("preco_prazo") is not None else base
        if base is None and compra is None and vista is None and prazo is None:
            return None

        # Valores atuais (antes)
        atual = Tabelaprecos.objects.using(self.db).filter(
            tabe_empr=self.empresa,
            tabe_fili=self.filial,
            tabe_prod=str(self.produto.prod_codi),
        ).first()
        ante_prco = getattr(atual, "tabe_prco", None) if atual else None
        ante_cuge = getattr(atual, "tabe_cuge", None) if atual else None
        ante_avis = getattr(atual, "tabe_avis", None) if atual else None
        ante_apra = getattr(atual, "tabe_apra", None) if atual else None

        # Novos valores
        novo_prco = (base if base is not None else (vista if vista is not None else (prazo if prazo is not None else compra)))
        dados_tabela = {
            "tabe_empr": self.empresa,
            "tabe_fili": self.filial,
            "tabe_prod": str(self.produto.prod_codi),
            "tabe_prco": novo_prco,
            "tabe_cuge": compra,
            "tabe_avis": vista,
            "tabe_apra": prazo,
        }

        # Atualiza/cria preço atual com filtro por empresa/filial/produto
        chave = {
            "tabe_empr": self.empresa,
            "tabe_fili": self.filial,
            "tabe_prod": str(self.produto.prod_codi),
        }
        update_fields = {
            k: v for k, v in dados_tabela.items()
            if k not in ("tabe_empr", "tabe_fili", "tabe_prod")
        }
        qs = Tabelaprecos.objects.using(self.db).filter(**chave)
        if qs.exists():
            qs.update(**update_fields)
            obj = qs.first()
        else:
            obj = Tabelaprecos.objects.using(self.db).create(**{**chave, **update_fields})

        # Criar registro de histórico com auto now
        hist = {
            "tabe_empr": self.empresa,
            "tabe_fili": self.filial,
            "tabe_prod": str(self.produto.prod_codi),
            "tabe_data_hora": timezone.now(),
            "tabe_prco_ante": ante_prco,
            "tabe_prco_novo": novo_prco,
            "tabe_cuge_ante": ante_cuge,
            "tabe_cuge_novo": compra,
            "tabe_avis_ante": ante_avis,
            "tabe_avis_novo": vista,
            "tabe_apra_ante": ante_apra,
            "tabe_apra_novo": prazo,
        }
        Tabelaprecoshist.objects.using(self.db).create(**hist)
        return obj
