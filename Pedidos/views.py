from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from .models import PedidoVenda
from .serializers import PedidoVendaSerializer

class PedidoVendaViewSet(viewsets.ModelViewSet):
    serializer_class = PedidoVendaSerializer
    queryset = PedidoVenda.objects.all().order_by('pedi_nume')
    filter_backends = [SearchFilter]
    lookup_field = 'pedi_nume'
    search_fields = ['pedi_nume', 'pedi_forn']
    
    def get_queryset(self):
        db_alias = getattr(self.request, 'db_alias', 'default')
        return PedidoVenda.objects.using(db_alias).all().order_by('pedi_nume')

    