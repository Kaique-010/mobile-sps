# views/pedidos.py
from rest_framework import viewsets
from .models import PedidosGeral
from .serializers import PedidosGeralSerializer
from core.registry import get_licenca_db_config
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from django_filters import rest_framework as filters


class PedidosGeralFilter(filters.FilterSet):
    data_inicial = filters.DateFilter(field_name='data_pedido', lookup_expr='gte')
    data_final = filters.DateFilter(field_name='data_pedido', lookup_expr='lte')
    nome_vendedor = filters.CharFilter(field_name='nome_vendedor', lookup_expr='icontains')
    nome_cliente = filters.CharFilter(field_name='nome_cliente', lookup_expr='icontains')
    empresa = filters.CharFilter(field_name='empresa', lookup_expr='icontains')
    filial = filters.CharFilter(field_name='filial', lookup_expr='icontains')

    class Meta:
        model = PedidosGeral
        fields = ['data_inicial', 'data_final', 'nome_vendedor', 'nome_cliente']


class PedidosGeralViewSet(ModuloRequeridoMixin, viewsets.ReadOnlyModelViewSet):
    modulo_necessario = ['dashboards', 'dash']
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = PedidosGeralFilter
    search_fields = ['nome_vendedor', 'nome_cliente']
    serializer_class = PedidosGeralSerializer
    pagination_class = None

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        queryset = PedidosGeral.objects.using(banco).all().order_by('-data_pedido', '-numero_pedido')

        empresa = self.request.query_params.get('empresa')
        filial = self.request.query_params.get('filial')

        if empresa:
            queryset = queryset.filter(empresa=empresa)
        if filial:
            queryset = queryset.filter(filial=filial)

        return queryset
