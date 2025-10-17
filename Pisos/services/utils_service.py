# services/utils_service.py
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation


def parse_decimal(value, default="0"):
    """Converte qualquer valor (str, float, None) em Decimal seguro."""
    if value is None:
        return Decimal(default)
    try:
        if isinstance(value, str):
            value = value.strip().replace(',', '.')
            if not value:
                return Decimal(default)
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)

def arredondar(valor, casas=2):
    if valor is None:
        return Decimal("0.00")
    return parse_decimal(valor).quantize(Decimal(10) ** -casas, rounding=ROUND_HALF_UP)



from Entidades.models import Entidades
from core.utils import get_licenca_db_config

class DadosEntidadesService:
    @staticmethod
    def preencher_dados_do_cliente(pedido, request):
        """
        Busca os dados da entidade e preenche no pedido antes de salvar.
        """
        banco = get_licenca_db_config(request)
        cliente = Entidades.objects.using(banco).filter(enti_clie=pedido.pedi_clie).first()

        if cliente:
            pedido.pedi_ende = cliente.enti_ende
            pedido.pedi_nume_ende = cliente.enti_nume
            pedido.pedi_cida = cliente.enti_cida
            pedido.pedi_esta = cliente.enti_esta
            pedido.pedi_comp = cliente.enti_comp

        return pedido
    
    @staticmethod
    def preencher_dados_cliente(orcamento, request):    
        """
        Busca os dados da entidade e preenche no orçamento antes de salvar.
        """
        banco = get_licenca_db_config(request)
        cliente = Entidades.objects.using(banco).filter(enti_clie=orcamento.orca_clie).first()

        if cliente:
            orcamento.orca_ende = cliente.enti_ende
            orcamento.orca_nume_ende = cliente.enti_nume
            orcamento.orca_cida = cliente.enti_cida
            orcamento.orca_esta = cliente.enti_esta
            orcamento.orca_comp = cliente.enti_comp

        return orcamento