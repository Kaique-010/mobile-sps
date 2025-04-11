from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from .models import PedidoVenda
from .serializers import PedidoVendaSerializer

class PedidoVendaViewSet(viewsets.ModelViewSet):
    queryset = PedidoVenda.objects.all().order_by('pedi_nume')
    serializer_class = PedidoVendaSerializer
    filter_backends = [SearchFilter]
    search_fields = ['pedi_nume', 'pédi_nume']

    