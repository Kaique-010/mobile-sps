from Entidades.models import Entidades


class ClienteEnderecoService:
    @staticmethod
    def preencher_orcamento(*, banco, orcamento):
        cliente = Entidades.objects.using(banco).filter(
            enti_clie=orcamento.orca_clie,
            enti_empr=orcamento.orca_empr,
        ).first()

        if not cliente:
            return orcamento

        orcamento.orca_ende = cliente.enti_ende
        orcamento.orca_nume_ende = cliente.enti_nume
        orcamento.orca_cida = cliente.enti_cida
        orcamento.orca_esta = cliente.enti_esta
        orcamento.orca_comp = cliente.enti_comp

        if hasattr(orcamento, "orca_bair"):
            orcamento.orca_bair = getattr(cliente, "enti_bair", None)

        return orcamento

    @staticmethod
    def preencher_pedido(*, banco, pedido):
        cliente = Entidades.objects.using(banco).filter(
            enti_clie=pedido.pedi_clie,
            enti_empr=pedido.pedi_empr,
        ).first()

        if not cliente:
            return pedido

        pedido.pedi_ende = cliente.enti_ende
        pedido.pedi_nume_ende = cliente.enti_nume
        pedido.pedi_cida = cliente.enti_cida
        pedido.pedi_esta = cliente.enti_esta
        pedido.pedi_comp = cliente.enti_comp

        if hasattr(pedido, "pedi_bair"):
            pedido.pedi_bair = getattr(cliente, "enti_bair", None)

        return pedido