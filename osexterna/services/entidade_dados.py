from Entidades.models import Entidades
from ..models import Osexterna
from core.utils import get_licenca_db_config


class DadosEntidadesService:
    @staticmethod
    def preencher_dados_do_cliente(osexterna, request):
        """
        Busca os dados da entidade e preenche no pedido antes de salvar.
        """
        banco = get_licenca_db_config(request)
        cliente = Entidades.objects.using(banco).filter(enti_clie=osexterna.osex_clie).first()

        if cliente:
            osexterna.osex_ende = cliente.enti_ende
            osexterna.osex_ende_nume = cliente.enti_nume
            osexterna.osex_cida = cliente.enti_cida
            osexterna.osex_bair = cliente.enti_bair
        return osexterna
