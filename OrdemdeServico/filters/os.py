# filters/os.py
from django_filters import rest_framework as filters
from ..models import OrdensEletro, Ordemservico
from Entidades.models import Entidades
from core.registry import get_licenca_db_config
import logging

logger = logging.getLogger(__name__)

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

class OrdemServicoFilter(filters.FilterSet):
    cliente_nome = filters.CharFilter(method='filter_cliente_nome')
    
    class Meta:
        model = Ordemservico
        fields = ['orde_stat_orde', 'orde_prio', 'orde_tipo', 'orde_enti']
    
    def filter_cliente_nome(self, queryset, name, value):
        if not value:
            return queryset
        
        # Obter o banco de dados do contexto
        # Tenta pegar da view ou do request
        banco = 'default'
        view = getattr(self, 'view', None)
        request = getattr(self, 'request', None) or (view.request if view else None)
        
        if request:
             banco = get_licenca_db_config(request) or 'default'

        # Buscar entidades que contenham o nome do cliente (busca parcial)
        try:
            entidades_ids = list(Entidades.objects.using(banco).filter(
                enti_nome__icontains=value
            ).values_list('enti_clie', flat=True))
            
            if entidades_ids:
                return queryset.filter(orde_enti__in=entidades_ids)
            else:
                return queryset.none()
        except Exception as e:
            logger.error(f"Erro ao filtrar cliente: {e}")
            return queryset
