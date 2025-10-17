from .utils_service import DadosEntidadesService, arredondar
from .calculo_services import calcular_ambientes, calcular_total_geral
from ..models import Itenspedidospisos

class PedidoService:
    @staticmethod
    def preparar_pedido(pedido, request):
        """
        Preenche dados do cliente e recalcula totais do pedido.
        """
        banco = pedido._state.db or 'default'

        DadosEntidadesService.preencher_dados_do_cliente(pedido, request)

        itens = Itenspedidospisos.objects.using(banco).filter(
            item_empr=pedido.pedi_empr,
            item_fili=pedido.pedi_fili,
            item_pedi=pedido.pedi_nume
        )

        if not itens.exists():
            pedido.pedi_tota = 0
            return pedido

        ambientes = calcular_ambientes(itens)
        total_geral = calcular_total_geral(ambientes)

        pedido.pedi_tota = arredondar(total_geral)
        return pedido
