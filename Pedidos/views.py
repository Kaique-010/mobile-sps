from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, NotFound
from core.registry import get_licenca_db_config
from .models import PedidoVenda
from .serializers import PedidoVendaSerializer
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from rest_framework.filters import SearchFilter


import logging
logger = logging.getLogger(__name__)


class PedidoVendaViewSet(ModuloRequeridoMixin,viewsets.ModelViewSet):
    modeulo_necessario = 'Pedidos'  
    permission_classes = [IsAuthenticated]
    serializer_class = PedidoVendaSerializer
    filter_backends = [SearchFilter]
    lookup_field = 'pedi_nume'
    search_fields = ['pedi_nume', 'pedi_forn']
    
    def get_queryset(self):
       banco = get_licenca_db_config(self.request)
       if banco:
          return PedidoVenda.objects.using(banco).all().order_by('pedi_nume')
       else:
        logger.error("Banco de dados não encontrado.")
        raise NotFound("Banco de dados não encontrado.")

