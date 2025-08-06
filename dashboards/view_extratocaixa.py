from .models import ExtratoCaixa
from .serializers import ExtratoCaixaSerializer
from core.decorator import ModuloRequeridoMixin
from core.middleware import get_licenca_slug
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from datetime import datetime, timedelta
from rest_framework.response import Response
from rest_framework.decorators import action


class ExtratoCaixaPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class ExtratoCaixaViewSet(ModelViewSet, ModuloRequeridoMixin):
    serializer_class = ExtratoCaixaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ('data', 'pedido', 'nome_cliente', 'forma_de_recebimento')
    search_fields = ('pedido', 'nome_cliente', 'produto', 'descricao', 'forma_de_recebimento')
    pagination_class = ExtratoCaixaPagination

    def get_queryset(self):
        slug = get_licenca_slug()
        if not slug:
            return ExtratoCaixa.objects.none()
        
        empresa = self.request.query_params.get('empresa')
        filial = self.request.query_params.get('filial')
        data_inicio = self.request.query_params.get('data_inicio')
        data_fim = self.request.query_params.get('data_fim')

        qs = ExtratoCaixa.objects.using(slug).all()
        
        # Filtros obrigatórios para performance
        if empresa:
            qs = qs.filter(empresa=empresa)
        if filial:
            qs = qs.filter(filial=filial)
            
        # Se não especificar datas, limita aos últimos 30 dias por padrão
        if not data_inicio and not data_fim:
            data_limite = datetime.now().date() - timedelta(days=30)
            qs = qs.filter(data__gte=data_limite)
        else:
            if data_inicio:
                qs = qs.filter(data__gte=data_inicio)
            if data_fim:
                qs = qs.filter(data__lte=data_fim)

        return qs.order_by('-data', '-pedido')

    @action(detail=False, methods=['get'])
    def resumo(self, request):
        """Endpoint otimizado para resumo sem paginação"""
        slug = get_licenca_slug()
        if not slug:
            return Response({"error": "Licença não encontrada"}, status=404)
            
        empresa = request.query_params.get('empresa')
        filial = request.query_params.get('filial')
        data_inicio = request.query_params.get('data_inicio')
        data_fim = request.query_params.get('data_fim')
        
        qs = ExtratoCaixa.objects.using(slug).all()
        
        if empresa:
            qs = qs.filter(empresa=empresa)
        if filial:
            qs = qs.filter(filial=filial)
        if data_inicio:
            qs = qs.filter(data__gte=data_inicio)
        if data_fim:
            qs = qs.filter(data__lte=data_fim)
            
        # Agregações para resumo
        from django.db.models import Sum, Count
        resumo = qs.aggregate(
            total_valor=Sum('valor_total'),
            total_registros=Count('pedido')
        )
        
        # Resumo por forma de recebimento
        formas_recebimento = qs.values('forma_de_recebimento').annotate(
            total=Sum('valor_total'),
            quantidade=Count('pedido')
        ).order_by('-total')
        
        return Response({
            'resumo_geral': resumo,
            'por_forma_recebimento': list(formas_recebimento)
        })

      
