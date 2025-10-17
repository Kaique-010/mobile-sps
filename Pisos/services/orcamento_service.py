from .utils_service import DadosEntidadesService, arredondar
from .calculo_services import calcular_ambientes, calcular_total_geral
from ..models import Itensorcapisos

class OrcamentoService:
    @staticmethod
    def preparar_orcamento(orcamento, request):
        """
        Preenche dados do cliente e recalcula totais do orçamento.
        """
        banco = orcamento._state.db or 'default'  # fallback seguro

        # 1️⃣ Preenche endereço e contato do cliente
        DadosEntidadesService.preencher_dados_cliente(orcamento, request)

        # 2️⃣ Recalcula totais com base nos itens já existentes
        itens = Itensorcapisos.objects.using(banco).filter(
            item_empr=orcamento.orca_empr,
            item_fili=orcamento.orca_fili,
            item_orca=orcamento.orca_nume
        )

        if not itens.exists():
            orcamento.orca_tota = 0
            return orcamento

        ambientes = calcular_ambientes(itens)
        total_geral = calcular_total_geral(ambientes)

        orcamento.orca_tota = arredondar(total_geral)
        return orcamento
