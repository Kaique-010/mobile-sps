

from Pedidos.models import PedidoVenda, PedidosGeral,Itenspedidovenda
from Orcamentos.models import Orcamentos,ItensOrcamento
from O_S.models import  Os
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from OrdemdeServico.models import Ordemservico
from Pedidos.rest.serializers import PedidoVendaSerializer, PedidosGeralSerializer, ItemPedidoVendaSerializer
from Orcamentos.rest.serializers import OrcamentosSerializer, ItemOrcamentoSerializer
from O_S.REST.serializers import OrdemServicoGeralSerializer, OsSerializer
from OrdemdeServico.serializers import OrdemServicoSerializer
from .base_cliente import BaseClienteViewSet
from core.excecoes import ErroDominio
from core.dominio_handler import tratar_erro, tratar_sucesso


class PedidosViewSet(BaseClienteViewSet):
    queryset = PedidoVenda.objects.all()
    serializer_class = PedidoVendaSerializer

class PedidosGeralViewSet(BaseClienteViewSet):
    queryset = PedidosGeral.objects.all()
    serializer_class = PedidosGeralSerializer

class ItensPedidosVendaViewSet(BaseClienteViewSet):
    queryset = Itenspedidovenda.objects.all()
    serializer_class = ItemPedidoVendaSerializer

class ItensOrcamentoViewSet(BaseClienteViewSet):
    queryset = ItensOrcamento.objects.all()
    serializer_class = ItemOrcamentoSerializer


class OrcamentosViewSet(BaseClienteViewSet):
    queryset = Orcamentos.objects.all()
    serializer_class = OrcamentosSerializer

class OrdemServicoViewSet(BaseClienteViewSet):
    queryset = Ordemservico.objects.all()
    serializer_class = OrdemServicoSerializer
    
    @action(detail=False, methods=['get'], url_path='em-estoque')
    def listar_ordem_em_estoque(self, request, *args, **kwargs):
        try:
            queryset = Ordemservico.objects.filter(orde_stat_orde=22)
            print("ordens em estoque:", queryset)
            serializer = self.serializer_class(queryset, many=True)
            return tratar_sucesso(serializer.data)
        except ErroDominio as e:
            return tratar_erro(e)
    
    

class OsViewSet(BaseClienteViewSet):
    queryset = Os.objects.all()
    serializer_class = OsSerializer