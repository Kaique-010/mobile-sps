from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from datetime import datetime
from core.registry import get_licenca_db_config
from .models import Contratosvendas
from core.decorator import ModuloRequeridoMixin
from .serializers import ContratosvendasSerializer


class ContratosViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    modulo_requerido = 'contratos'
    serializer_class = ContratosvendasSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'cont_cont': ['exact'],
        'cont_clie': ['exact', 'icontains'],
        'cont_data': ['exact'],
        'cont_prod': ['exact', 'icontains'],
    }
    search_fields = ['cont_cont', 'cont_clie']
    ordering_fields = ['cont_cont', 'cont_data']
    ordering = ['cont_cont']

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)

        if banco:
            data_minima = datetime(1900, 1, 1)
            return Contratosvendas.objects.using(banco).filter(
                Q(cont_data__gte=data_minima) |
                Q(cont_venc__gte=data_minima)
            )

        return Contratosvendas.objects.none()

    def get_serializer_class(self):
        return ContratosvendasSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context
