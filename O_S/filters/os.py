# filters/os.py
from django_filters import rest_framework as filters
from O_S.models import OrdemServicoGeral

class OrdemServicoGeralFilter(filters.FilterSet):
    data_inicial = filters.DateFilter(field_name='data_abertura', lookup_expr='gte')
    data_final = filters.DateFilter(field_name='data_abertura', lookup_expr='lte')

    cliente = filters.NumberFilter(field_name='cliente')
    nome_cliente = filters.CharFilter(field_name='nome_cliente', lookup_expr='icontains')

    vendedor = filters.NumberFilter(field_name='vendedor')
    nome_vendedor = filters.CharFilter(field_name='nome_vendedor', lookup_expr='icontains')

    responsavel = filters.NumberFilter(field_name='responsavel')
    atendente = filters.CharFilter(field_name='atendente', lookup_expr='icontains')

    status_os = filters.CharFilter(field_name='status_os', lookup_expr='icontains')  # status como texto
    ordem_de_servico = filters.NumberFilter(field_name='ordem_de_servico')

    class Meta:
        model = OrdemServicoGeral
        fields = [
            'data_inicial', 'data_final',
            'cliente', 'nome_cliente',
            'vendedor', 'nome_vendedor',
            'responsavel', 'atendente',
            'status_os', 'ordem_de_servico'
        ]
