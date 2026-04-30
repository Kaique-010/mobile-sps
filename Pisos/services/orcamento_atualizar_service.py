from decimal import Decimal
from django.db import transaction

from Pisos.models import Orcamentopisos, Itensorcapisos
from Pisos.services.orcamento_criar_service import OrcamentoCriarService
from Pisos.services.utils_service import parse_decimal, arredondar


class OrcamentoAtualizarService:
    def executar(self, *, banco, orcamento, dados, itens):
        if not itens:
            raise ValueError("Itens do orçamento são obrigatórios.")

        with transaction.atomic(using=banco):
            dados_orcamento = dict(dados)
            dados_orcamento.pop("itens_input", None)
            dados_orcamento.pop("itens", None)
            dados_orcamento.pop("parametros", None)

            for campo, valor in dados_orcamento.items():
                setattr(orcamento, campo, valor)

            Itensorcapisos.objects.using(banco).filter(
                item_empr=orcamento.orca_empr,
                item_fili=orcamento.orca_fili,
                item_orca=orcamento.orca_nume,
            ).delete()

            total = OrcamentoCriarService()._criar_itens(
                banco=banco,
                orcamento=orcamento,
                itens=itens,
            )

            desconto = parse_decimal(getattr(orcamento, "orca_desc", 0))
            frete = parse_decimal(getattr(orcamento, "orca_fret", 0))

            orcamento.orca_tota = arredondar(total - desconto + frete)
            orcamento.save(using=banco)

            return orcamento