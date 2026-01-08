# views/os.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter

from .models import  OrdensEletro
from .serializers import OrdensEletroSerializer    
from .filters.os import OrdensEletroFilter
from core.registry import get_licenca_db_config
from core.decorator import ModuloRequeridoMixin

class OrdensEletroViewSet(ModuloRequeridoMixin, viewsets.ReadOnlyModelViewSet):
    modulo_necessario = 'ordemdeservico'
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = OrdensEletroFilter
    search_fields = ['nome_cliente', 'setor_nome', 'nome_responsavel', 'ordem_de_servico', 'pedido_compra', 'nf_entrada']
    serializer_class = OrdensEletroSerializer

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        return OrdensEletro.objects.using(banco).all().order_by('-data_abertura', '-ordem_de_servico')
        
