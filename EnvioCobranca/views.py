from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend

from .models import EnviarCobranca
from .serializers import EnviarCobrancaSerializer
from core.middleware import get_licenca_slug
from core.decorator import ModuloRequeridoMixin


class EnviarCobrancaViewSet(ReadOnlyModelViewSet, ModuloRequeridoMixin):
    serializer_class = EnviarCobrancaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ('empresa', 'filial', 'cliente_id', 'vencimento')
    search_fields = ('cliente_nome', 'numero_titulo', 'linha_digitavel')
    ordering_fields = ('vencimento', 'valor', 'cliente_nome')

    def get_queryset(self):
        slug = get_licenca_slug()
        if not slug:
            return EnviarCobranca.objects.none()
        
        qs = EnviarCobranca.objects.using(slug).all()

        # Filtro de data por query string
        data_ini = self.request.query_params.get('data_ini')
        data_fim = self.request.query_params.get('data_fim')
        if data_ini and data_fim:
            qs = qs.filter(vencimento__range=[data_ini, data_fim])

        return qs
