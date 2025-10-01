# filters/os.py
from django_filters import rest_framework as filters
from ..models import OrdensEletro

class OrdensEletroFilter(filters.FilterSet):
    data_inicial = filters.DateFilter(field_name='data_abertura', lookup_expr='gte')
    data_final = filters.DateFilter(field_name='data_abertura', lookup_expr='lte')

    cliente = filters.NumberFilter(field_name='cliente')
    nome_cliente = filters.CharFilter(field_name='nome_cliente', lookup_expr='icontains')

    setor = filters.NumberFilter(field_name='setor')
    setor_nome = filters.CharFilter(field_name='setor_nome', lookup_expr='icontains')

    responsavel = filters.NumberFilter(field_name='responsavel')
    nome_responsavel = filters.CharFilter(field_name='nome_responsavel', lookup_expr='icontains')

    status_ordem = filters.CharFilter(field_name='status_ordem', lookup_expr='icontains')
    ordem_de_servico = filters.NumberFilter(field_name='ordem_de_servico')

    # Filtros adicionais para melhor busca
    empresa = filters.NumberFilter(field_name='empresa')
    filial = filters.NumberFilter(field_name='filial')
    potencia = filters.CharFilter(field_name='potencia', lookup_expr='icontains')

    class Meta:
        model = OrdensEletro
        fields = [
            'data_inicial', 'data_final',
            'cliente', 'nome_cliente',
            'setor', 'setor_nome',
            'responsavel', 'nome_responsavel',
            'status_ordem', 'ordem_de_servico',
            'empresa', 'filial', 'potencia'
        ]
