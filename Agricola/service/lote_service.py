from .sequencial_Service import SequencialService
from ..models import LoteProdutos, SequencialControle
from django.db import transaction


class LoteService:

    @staticmethod
    def criar_lote(*, data, using):

        if not data.get("lote_ident"):
            numero = SequencialService.gerar(
                empresa=data["lote_empr"],
                filial=data["lote_fili"],
                tipo="LOTE",
                chave_extra=data["lote_prod"],  
                using=using,
            )

            data["lote_ident"] = str(numero).zfill(4)

        return LoteProdutos.objects.using(using).create(**data)
