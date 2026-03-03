from rest_framework.pagination import LimitOffsetPagination


class OrdemServicoPagination(LimitOffsetPagination):
    """Paginação customizada para Ordens de Serviço"""
    default_limit = 350    
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    max_limit = 350     # Limite máximo
