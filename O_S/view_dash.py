# views/os.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter

from .models import OrdemServicoGeral
from .REST.serializers import OrdemServicoGeralSerializer
from .filters.os import OrdemServicoGeralFilter
from core.registry import get_licenca_db_config
from core.decorator import ModuloRequeridoMixin

class OrdemServicoGeralViewSet(ModuloRequeridoMixin, viewsets.ReadOnlyModelViewSet):
    modulo_necessario = 'O_S'
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = OrdemServicoGeralFilter
    search_fields = ['nome_cliente', 'nome_vendedor', 'atendente']
    serializer_class = OrdemServicoGeralSerializer

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        return OrdemServicoGeral.objects.using(banco).all().order_by('-data_abertura', '-ordem_de_servico')
