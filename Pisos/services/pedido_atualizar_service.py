from decimal import Decimal
from django.db import transaction

from Pisos.models import Pedidospisos, Itenspedidospisos
from Pisos.services.pedido_criar_service import PedidoCriarService
from Pisos.services.utils_service import parse_decimal, arredondar


class PedidoAtualizarService:
    def executar(self, *, banco, pedido, dados, itens):
        if not itens:
            raise ValueError("Itens do pedido são obrigatórios.")

        with transaction.atomic(using=banco):
            dados_pedido = dict(dados)

            dados_pedido.pop("itens_input", None)
            dados_pedido.pop("itens", None)
            dados_pedido.pop("parametros", None)

            # Atualiza campos
            for campo, valor in dados_pedido.items():
                setattr(pedido, campo, valor)

            # Remove itens antigos
            Itenspedidospisos.objects.using(banco).filter(
                item_empr=pedido.pedi_empr,
                item_fili=pedido.pedi_fili,
                item_pedi=pedido.pedi_nume,
            ).delete()

            # Recria itens (reutiliza lógica do criar)
            total = PedidoCriarService()._criar_itens(
                banco=banco,
                pedido=pedido,
                itens=itens,
            )

            desconto = parse_decimal(getattr(pedido, "pedi_desc", 0))
            frete = parse_decimal(getattr(pedido, "pedi_fret", 0))

            pedido.pedi_tota = arredondar(total - desconto + frete)

            pedido.save(using=banco)

            return pedido