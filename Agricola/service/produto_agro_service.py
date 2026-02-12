from .sequencial_Service import SequencialService
from ..models import ProdutoAgro, SequencialControle
from django.db import transaction

class ProdutoAgroService:

    @staticmethod
    def criar_produto(*, data, using):

        if not data.get("prod_codi_agro"):
            numero = SequencialService.gerar(
                empresa=data["prod_empr_agro"],
                filial=data["prod_fili_agro"],
                tipo="PRODUTO",
                using=using,
            )

            data["prod_codi_agro"] = str(numero).zfill(6)

        return ProdutoAgro.objects.using(using).create(**data)


