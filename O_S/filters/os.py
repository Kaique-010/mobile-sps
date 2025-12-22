# filters/os.py
from django_filters import rest_framework as filters
from O_S.models import OrdemServicoGeral, Os
from Entidades.models import Entidades

class OsFilter(filters.FilterSet):
    os_os = filters.NumberFilter(field_name='os_os')
    os_stat_os = filters.NumberFilter(field_name='os_stat_os')
    os_clie = filters.NumberFilter(field_name='os_clie')
    os_empr = filters.NumberFilter(field_name='os_empr')
    os_fili = filters.NumberFilter(field_name='os_fili')
    
    # Custom filter for client name
    cliente_nome = filters.CharFilter(method='filter_cliente_nome')

    class Meta:
        model = Os
        fields = ['os_os', 'os_stat_os', 'os_clie', 'os_empr', 'os_fili']

    def filter_cliente_nome(self, queryset, name, value):
        if not value:
            return queryset
        
        # Filter Entidades by name and get IDs
        db_alias = queryset.db 
        
        clientes_ids = list(Entidades.objects.using(db_alias).filter(
            enti_nome__icontains=value
        ).values_list('enti_clie', flat=True)[:200])
        
        return queryset.filter(os_clie__in=clientes_ids)

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
